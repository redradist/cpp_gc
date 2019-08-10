/**
 * @file gc_ptr.hpp
 * @author Denis Kotov
 * @date 31 Jul 2019
 * @brief Contains gc_ptr class.
 * It is thread safe Deterministic Garbage Pointer Collector
 * @copyright Denis Kotov, MIT License. Open source: https://github.com/redradist/DeterministicGarbagePointer/blob/master/gc_ptr.hpp
 */

#ifndef DETERMINISTIC_GARBAGE_COLLECTOR_POINTER_HPP
#define DETERMINISTIC_GARBAGE_COLLECTOR_POINTER_HPP

#include <atomic>
#include <vector>
#include <unordered_set>
#include <mutex>
#include <type_traits>
#include <thread>

namespace memory {

namespace synchronization {

class SpinLock {
 public:
  SpinLock(std::atomic_flag & lockObject)
      : lock_object_{lockObject} {
    while (lock_object_.test_and_set(std::memory_order_acquire));
  }

  ~SpinLock() {
    lock_object_.clear(std::memory_order_release);
  }

 private:
  std::atomic_flag & lock_object_;
};

}

template <typename T>
class has_use_gc_ptr
{
  typedef char one;
  struct two { char x[2]; };

  template <typename C> static one testConnectToRoot( typeof(&C::connectToRoot) ) ;
  template <typename C> static two testConnectToRoot(...);

  template <typename C> static one testDisconnectFromRoot( typeof(&C::disconnectFromRoot) ) ;
  template <typename C> static two testDisconnectFromRoot(...);

 public:
  enum { value = sizeof(testConnectToRoot<T>(0)) == sizeof(char) &&
                 sizeof(testDisconnectFromRoot<T>(0)) == sizeof(char)};
};

struct gc_object_control_block {
  const bool is_aligned_memory_ = false;
  std::atomic_flag lock_object_ = ATOMIC_FLAG_INIT;
  std::unordered_map<void *, uint32_t> root_ptrs_;
};

template <typename TObject>
struct gc_object_aligned_storage {
  TObject object_;
  gc_object_control_block control_block_;
};

template <typename TObject>
class gc_ptr {
 public:
  gc_ptr()
    : root_ptrs_{this} {
  }

  explicit gc_ptr(TObject * objectPtr)
    : root_ptrs_{this} {
    object_ptr_ = objectPtr;
    object_control_block_ptr_ = new gc_object_control_block{};
    for (auto & rootRefPtr : this->root_ptrs_) {
      addRootPtrToObject(rootRefPtr);
    }
  }

  gc_ptr(const gc_ptr & gcPtr)
    : root_ptrs_{this} {
    this->operator=(gcPtr);
  }

  ~gc_ptr() {
    removeAllRoots();
  }

  template <typename ... TArgs>
  void create_object(TArgs && ... args) {
    removeAllRoots();
    auto gcObjectAlignedStoragePtr = new gc_object_aligned_storage<TObject>{
        {std::forward<TObject>(args)...},
        {true, ATOMIC_FLAG_INIT, {}}
    };
    object_ptr_ = &gcObjectAlignedStoragePtr->object_;
    object_control_block_ptr_ = &gcObjectAlignedStoragePtr->control_block_;
    addAllRoots();
  }

  explicit operator bool() const noexcept {
    return object_ptr_ != nullptr;
  }

  TObject & operator *() const {
    return *object_ptr_;
  }

  TObject * operator->() const noexcept {
    return object_ptr_;
  }

  gc_ptr & operator=(TObject * const objectPtr) {
    removeAllRoots();
    object_ptr_ = objectPtr;
    if (object_ptr_ != nullptr) {
      object_control_block_ptr_ = new gc_object_control_block{};
    } else {
      object_control_block_ptr_ = nullptr;
    }
    addAllRoots();
    return *this;
  }

  gc_ptr & operator=(const gc_ptr & objectPtr) {
    removeAllRoots();
    object_ptr_ = objectPtr.object_ptr_;
    object_control_block_ptr_ = objectPtr.object_control_block_ptr_;
    addAllRoots();
    return *this;
  }

  void connectToRoot(void * rootPtr) {
    root_ptrs_.insert(rootPtr);
    addRootPtrToObject(rootPtr);
    if (is_root_) {
      is_root_ = false;
      disconnectFromRoot(true, this);
    }
  }

  void disconnectFromRoot(bool isRoot, void * rootPtr) {
    root_ptrs_.erase(rootPtr);
    removeRootPtrFromObject(isRoot, rootPtr);
  }

 protected:
  void addAllRoots() {
    if (object_control_block_ptr_ != nullptr) {
      auto rootPtrs = root_ptrs_;
      for (auto &rootRefPtr : rootPtrs) {
        addRootPtrToObject(rootRefPtr);
      }
    }
  }

  void removeAllRoots() {
    if (object_control_block_ptr_ != nullptr) {
      auto rootPtrs = root_ptrs_;
      for (auto &rootRefPtr : rootPtrs) {
        root_ptrs_.erase(rootRefPtr);
        removeRootPtrFromObject(is_root_, rootRefPtr);
      }
    }
  }

  void addRootPtrToObject(void *rootPtr) const {
    if (object_control_block_ptr_ != nullptr) {
      bool isNewRoot;
      {
        synchronization::SpinLock lock{object_control_block_ptr_->lock_object_};
        isNewRoot = object_control_block_ptr_->root_ptrs_.count(rootPtr) == 0;
        if (isNewRoot) {
          object_control_block_ptr_->root_ptrs_[rootPtr] = 1;
        } else {
          object_control_block_ptr_->root_ptrs_[rootPtr] += 1;
        }
      }
      if (isNewRoot) {
        if constexpr (has_use_gc_ptr<TObject>::value) {
          object_ptr_->connectToRoot(rootPtr);
        }
      }
    }
  }

  void removeRootPtrFromObject(bool isRoot, void *rootPtr) {
    if (object_control_block_ptr_ != nullptr) {
      bool isRemovedRoot = false;
      bool isNoRoots;
      {
        synchronization::SpinLock lock{object_control_block_ptr_->lock_object_};
        if (isRoot) {
          if (object_control_block_ptr_->root_ptrs_.count(rootPtr) > 0) {
            object_control_block_ptr_->root_ptrs_.erase(rootPtr);
            isRemovedRoot = true;
          }
        } else if (object_control_block_ptr_->root_ptrs_.count(rootPtr) > 0) {
          object_control_block_ptr_->root_ptrs_[rootPtr] -= 1;
          if (object_control_block_ptr_->root_ptrs_[rootPtr] == 0) {
            object_control_block_ptr_->root_ptrs_.erase(rootPtr);
            isRemovedRoot = true;
          }
        }
        isNoRoots = object_control_block_ptr_->root_ptrs_.empty();
      }
      if (isRemovedRoot) {
        if constexpr (has_use_gc_ptr<TObject>::value) {
          object_ptr_->disconnectFromRoot(isRoot, rootPtr);
        }
      }
      if (isRemovedRoot && isNoRoots) {
        if (object_control_block_ptr_->is_aligned_memory_) {
          auto gcObjectAlignedStoragePtr = reinterpret_cast<gc_object_aligned_storage<TObject>*>(object_ptr_);
          delete gcObjectAlignedStoragePtr;
        } else {
          delete object_ptr_;
          delete object_control_block_ptr_;
        }
        object_ptr_ = nullptr;
        object_control_block_ptr_ = nullptr;
      } else if (root_ptrs_.empty()) {
        object_ptr_ = nullptr;
        object_control_block_ptr_ = nullptr;
      }
    }
  }

  bool is_root_ = true;
  std::unordered_set<void *> root_ptrs_;
  TObject * object_ptr_ = nullptr;
  gc_object_control_block * object_control_block_ptr_ = nullptr;
};

}

#endif  //DETERMINISTIC_GARBAGE_COLLECTOR_POINTER_HPP
