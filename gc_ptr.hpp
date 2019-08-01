//
// Created by redra on 31.07.19.
//

#ifndef DETERMINISTIC_GARBAGE_COLLECTOR_POINTER_HPP
#define DETERMINISTIC_GARBAGE_COLLECTOR_POINTER_HPP

#include <atomic>
#include <vector>
#include <unordered_set>
#include <mutex>
#include <type_traits>
#include <thread>

namespace gc::memory {

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
  std::atomic_flag lock_object_ = ATOMIC_FLAG_INIT;
  std::unordered_set<void *> root_ptrs_;
};

template <typename TObject>
struct gc_object_aligned_storage {
  TObject object_;
  gc_object_control_block control_block_;
};

template <typename TObject>
class gc_ptr {
 public:
  gc_ptr() = default;

  explicit gc_ptr(TObject * objectPtr) {
    object_ptr_ = objectPtr;
    object_control_block_ptr_ = new gc_object_control_block{};
    for (auto & rootRefPtr : this->root_ptrs_) {
      connectRootPtr(rootRefPtr);
    }
  }

  gc_ptr(const gc_ptr & gcPtr) {
    this->operator=(gcPtr);
  }

  gc_ptr(gc_ptr && gcPtr) {
    this->operator=(std::move(gcPtr));
  }

  ~gc_ptr() {
    if (object_control_block_ptr_ != nullptr) {
      for (auto & rootRefPtr : root_ptrs_) {
        removeRootPtr(rootRefPtr);
      }
    }
  }

  template <typename ... TArgs>
  void create_object(TArgs && ... args) {
    auto gcObjectAlignedStoragePtr = new gc_object_aligned_storage<TObject>{
        {std::forward<TObject>(args)...},
        {}
    };
    is_aligned_memory_ = true;
    object_ptr_ = &gcObjectAlignedStoragePtr->object_;
    object_control_block_ptr_ = &gcObjectAlignedStoragePtr->control_block_;
    for (auto & rootRefPtr : root_ptrs_) {
      connectRootPtr(rootRefPtr);
    }
  }

  explicit operator bool() const noexcept {
    return object_ptr_ != nullptr;
  }

  TObject * operator->() const noexcept {
    return object_ptr_;
  }

  gc_ptr & operator=(const TObject * objectPtr) {
    if (object_control_block_ptr_ != nullptr) {
      for (auto & rootRefPtr : root_ptrs_) {
        removeRootPtr(rootRefPtr);
      }
    }
    is_aligned_memory_ = false;
    object_ptr_ = objectPtr;
    object_control_block_ptr_ = new gc_object_control_block{};
    for (auto & rootRefPtr : root_ptrs_) {
      connectRootPtr(rootRefPtr);
    }
    return *this;
  }

  gc_ptr & operator=(const gc_ptr & objectPtr) {
    if (object_control_block_ptr_ != nullptr) {
      for (auto & rootRefPtr : root_ptrs_) {
        removeRootPtr(rootRefPtr);
      }
    }
    is_aligned_memory_ = objectPtr.is_aligned_memory_;
    object_ptr_ = objectPtr.object_ptr_;
    object_control_block_ptr_ = objectPtr.object_control_block_ptr_;
    for (auto & rootRefPtr : root_ptrs_) {
      connectRootPtr(rootRefPtr);
    }
    return *this;
  }

  gc_ptr & operator=(gc_ptr && objectPtr) {
    if (object_control_block_ptr_ != nullptr) {
      for (auto & rootRefPtr : root_ptrs_) {
        removeRootPtr(rootRefPtr);
      }
    }
    is_aligned_memory_ = objectPtr.is_aligned_memory_;
    object_ptr_ = objectPtr.object_ptr_;
    object_control_block_ptr_ = objectPtr.object_control_block_ptr_;
    objectPtr.is_aligned_memory_ = false;
    objectPtr.object_ptr_ = nullptr;
    objectPtr.object_control_block_ptr_ = nullptr;
    for (auto & rootRefPtr : root_ptrs_) {
      connectRootPtr(rootRefPtr);
    }
    return *this;
  }

  void connectToRoot(void * rootPtr) {
    root_ptrs_.insert(rootPtr);
    connectRootPtr(rootPtr);
  }

  void connectRootPtr(void * rootPtr) const {
    if (object_control_block_ptr_ != nullptr &&
        visited_objects.end() == visited_objects.find(object_control_block_ptr_)) {
      visited_objects.insert(object_control_block_ptr_);
      if constexpr (has_use_gc_ptr<TObject>::value) {
        object_ptr_->connectToRoot(rootPtr);
      }
      {
        synchronization::SpinLock lock{object_control_block_ptr_->lock_object_};
        object_control_block_ptr_->root_ptrs_.emplace(rootPtr);
      }
      visited_objects.erase(object_control_block_ptr_);
    }
  }

  void disconnectFromRoot(void * rootPtr) {
    root_ptrs_.erase(rootPtr);
    removeRootPtr(rootPtr);
  }

  void removeRootPtr(void * rootPtr) {
    if (object_control_block_ptr_ != nullptr &&
        visited_objects.end() == visited_objects.find(object_control_block_ptr_)) {
      visited_objects.insert(object_control_block_ptr_);
      if constexpr (has_use_gc_ptr<TObject>::value) {
        object_ptr_->disconnectFromRoot(rootPtr);
      }
      {
        synchronization::SpinLock lock{object_control_block_ptr_->lock_object_};
        object_control_block_ptr_->root_ptrs_.erase(rootPtr);
        visited_objects.erase(object_control_block_ptr_);
        if (object_control_block_ptr_->root_ptrs_.empty()) {
          if (is_aligned_memory_) {
            auto gcObjectAlignedStoragePtr = reinterpret_cast<gc_object_aligned_storage<TObject>*>(object_ptr_);
            delete gcObjectAlignedStoragePtr;
          } else {
            is_aligned_memory_ = false;
            delete object_ptr_;
            delete object_control_block_ptr_;
          }
        }
      }
    }
  }

 protected:
  static inline thread_local std::unordered_set<void *> visited_objects;

  std::unordered_set<void *> root_ptrs_;

  bool is_aligned_memory_ = false;
  TObject * object_ptr_ = nullptr;
  gc_object_control_block * object_control_block_ptr_ = nullptr;
};

template <typename TObject>
class root_gc_ptr : public gc_ptr<TObject> {
 public:
  root_gc_ptr() {
    this->root_ptrs_.insert(this);
  }

  root_gc_ptr(TObject * objectPtr) {
    this->root_ptrs_.insert(this);
    this->object_ptr_ = objectPtr;
    this->object_control_block_ptr_ = new gc_object_control_block{};
    for (auto & rootRefPtr : this->root_ptrs_) {
      this->connectRootPtr(rootRefPtr);
    }
  }
};

}

#endif  //DETERMINISTIC_GARBAGE_COLLECTOR_POINTER_HPP
