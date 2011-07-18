# Motivation
TODO: write.

# Data Structures
Flow-conduit _simulates global state_ through the `SymbolTable` class. 

# Algorithms
For each function, the user supplies a set of input and output _symbols_ (variable names). `ControlGraph` then constructs _data dependency_ and _data supplier_ maps. The data dependency map maps a function (_task_) to the set of names of variables (_symbols_) on which the task depends. The data supplier map maps each symbol to the function which returns that symbol. From these maps, `ControlGraph` assembles a `dependency graph` whose vertices are functions and whose edges (u,v) denote that function u directly depends on some symbol(s) provided by function v.

All functions are modified to take and return `SymbolTable`s as explained above.

I use _function_ and _vertex_ interchangeably when referring to the dependency graph.

For parallelism, flow-conduit maintains a fixed number of threads in `ThreadPool`, configurable for each run. Because we do not know ahead of time how long tasks take to finish, after each task completes, flow-condit dynamically schedules any new tasks that can now be run, in the following manner:

1. Construct the _dependency graph_ from _data dependency_ and _data supplier maps_. (`ControlGraph.finalize()`)
2. Transpose the dependency graph to a precedence graph and topologically sort the precedence graph. If we detect a cycle, raise a `CycleError` exception.
3. Construct the set `sources` to contain all vertices (functions) in the dependency graph which depend on no other functions.
4. Construct a worker pool with a fixed number of threads and a synchronous queue. The workers consume work units from the queue, and the queue accepts insertion of items.
5. Initialize a counter of unsubmitted tasks equal to the total number of tasks.
6. For each `s` in `sources`, enqueue a work unit consisting of applying the function `s` to a new, empty `SymbolTable`, and decrement the unsubmitted task counter.
7. _(Child Thread.)_ As each function `g` finishes,
    1. Synchronously record the result (a new `SymbolTable`) of this work unit.
    2. For each function `f` which depends on the current function:
        1. Synchronously check whether all of `f`'s dependencies are satisfied. If so, enqueue a work unit consisting of applying the function `f` to a `SymbolTable` whose parents are the results of all of the dependencies of `f`. _The parent relationship of the SymbolTable parallels the dependency relationship of ControlGraph. If `f` depends on `g` and `h`, then `f` will return a `SymbolTable` `t` which directly contains `f`'s output symbols, as well as parent pointers to the return values of `g` and `h`._
        2. Synchronously decrement the unsubmitted tasks counter.
        3. If there are zero unsubmitted tasks, notify the parent thread that all submissions are done.
8. _(Parent Thread.)_ Wait for the notification that all tasks are submitted. Then wait for the worker pool to finish.
9. Look up the requested symbols in our results and return them. 

# Next Steps
Currently we use the `threading` module, which is not ideal due to Python's Global Interpreter Lock. However, 

I plan to implement efficient memoization and serialization of `SymbolTableFunc` and `SymbolTable`. `SymbolTable` already implements structural sharing, so the idea is to exploit this property to cache and serialize intermediate results and identify when a function can be served from the cache.

`SymbolTable` should also be editable while maintaining structural sharing. I may then implement a simple database for storing intermediate results.

