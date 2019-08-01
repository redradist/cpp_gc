//
// Created by redra on 31.07.19.
//

#ifndef NOMOREGARBADGECOLLECTOR_GV_PTR_HPP
#define NOMOREGARBADGECOLLECTOR_GC_PTR_HPP

#include <iostream>
#include <atomic>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <deque>
#include <mutex>
#include <algorithm>
#include <type_traits>
#include <thread>

namespace icc::memory {

template <typename T>
class has_connect_to_root
{
  typedef char one;
  struct two { char x[2]; };

  template <typename C> static one test( typeof(&C::connectToRoot) ) ;
  template <typename C> static two test(...);

 public:
  enum { value = sizeof(test<T>(0)) == sizeof(char) };
};

template <typename T>
class has_disconnect_from_root
{
  typedef char one;
  struct two { char x[2]; };

  template <typename C> static one test( typeof(&C::disconnectFromRoot) ) ;
  template <typename C> static two test(...);

 public:
  enum { value = sizeof(test<T>(0)) == sizeof(char) };
};

struct gc_object_control_block {
  std::atomic_bool lock_{true};
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

  explicit operator bool() const {
    return object_ptr_ != nullptr;
  }

  TObject * operator->() const {
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

  gc_ptr & operator=(gc_ptr && objectPtr) noexcept {
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
    if (object_control_block_ptr_ != nullptr && object_control_block_ptr_->lock_) {
      object_control_block_ptr_->lock_ = false;
      if constexpr (has_connect_to_root<TObject>::value) {
        object_ptr_->connectToRoot(rootPtr);
      }
      object_control_block_ptr_->root_ptrs_.emplace(rootPtr);
      object_control_block_ptr_->lock_ = true;
    }
  }

  void disconnectFromRoot(void * rootPtr) {
    root_ptrs_.erase(rootPtr);
    removeRootPtr(rootPtr);
  }

  void removeRootPtr(void * rootPtr) {
    if (object_control_block_ptr_ != nullptr && object_control_block_ptr_->lock_) {
      object_control_block_ptr_->lock_ = false;
      if constexpr (has_disconnect_from_root<TObject>::value) {
        object_ptr_->disconnectFromRoot(rootPtr);
      }
      object_control_block_ptr_->root_ptrs_.erase(rootPtr);
      object_control_block_ptr_->lock_ = true;
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

 protected:
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

#endif //NOMOREGARBADGECOLLECTOR_GV_PTR_HPP
