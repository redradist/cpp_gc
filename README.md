## Intruduction

Consider the following example:
```cpp
#include <iostream>
#include <memory>

class Child;

class Parent {
 public:
  Parent() {
    std::cout << "Parent()" << std::endl;
  }

  ~Parent() {
    std::cout << "~Parent()" << std::endl;
  }

  void createChild() {
    child_ptr_ = std::make_shared<Child>();
  }

  std::shared_ptr<Child> getChild() {
    return child_ptr_;
  }

 private:
  std::shared_ptr<Child> child_ptr_;
};

class Child {
 public:
  Child() {
    std::cout << "Child()" << std::endl;
  }

  ~Child() {
    std::cout << "~Child()" << std::endl;
  }

  void setParent(std::shared_ptr<Parent> parentPtr) {
    parent_ptr_ = parentPtr;
  }

 private:
  std::shared_ptr<Parent> parent_ptr_;
};

int main() {
  auto parent = std::make_shared<Parent>();
  parent->createChild();
  parent->getChild()->setParent(parent);
  return 0;
}
```

In this example you will get memory leak due to cyclic dependecy ... :(

To fix it you should be very careful and use in Child class instead of std::shared_ptr<Parent> -> std::weak_ptr<Parent> as in example below:

```cpp
...

class Child {

  ...

  void setParent(std::shared_ptr<Parent> parentPtr) {
    parent_ptr_ = parentPtr;
  }

 private:
  std::weak_ptr<Parent> parent_ptr_;
};

...
```

But what if we can combine determinism of std::shared_ptr and garbadge collector ??

memory::gc_ptr is exactly for this purpose !!
Consider the follwoing example:

```cpp
#include <iostream>
#include "gc_ptr.hpp"

class Child;

class Parent {
 public:
  Parent() {
    std::cout << "Parent()" << std::endl;
  }

  ~Parent() {
    std::cout << "~Parent()" << std::endl;
  }

  void createChild() {
    child_ptr_.create_object();
  }

  memory::gc_ptr<Child> getChild() {
    return child_ptr_;
  }

 private:
  memory::gc_ptr<Child> child_ptr_;
};

class Child {
 public:
  Child() {
    std::cout << "Child()" << std::endl;
  }

  ~Child() {
    std::cout << "~Child()" << std::endl;
  }

  void setParent(memory::gc_ptr<Parent> parentPtr) {
    parent_ptr_ = parentPtr;
  }

 private:
  memory::gc_ptr<Parent> parent_ptr_;
};

int main() {
  memory::gc_ptr<Parent> parent;
  parent.create_object();
  parent->createChild();
  parent->getChild()->setParent(parent);
  return 0;
}
```

This code is easier that you should not track possible cyclic dependecies by eyes and still you will get deterministic behaviour

## How to use it
On Ubuntu:
```console
sudo apt-get install libclang
sudo python3 -m pip install clang
```

Then in your cmake based project add the following line before project directive:
```cmake

...
set(CMAKE_CXX_COMPILER <path_to_clang_extras.py>)
project(<project_name>)
...

For more information how to use take a look at example folder
Enjoy ;)
```
