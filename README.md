# Anytime mini-batch implementation on Tensorflow

## Tutorial/sample code for using AMB implementation
* [`run_sample_code.py`](src/run_sample_code.py) includes a sample code. See the comments therewithin.
* Run the code with `mpirun -n 3 python -u run_sample_code.py` (master and two workers).
* Toggle `is_distributed` boolean to run in distributed or non-distributed manner.

### Package requirements
* Execute following commands to check the versions of `python`, `numpy`, `mpi4py` and `tensorflow`.
```
python --version
python -c 'import numpy; print(numpy.__version__)'
python -c 'import mpi4py; print(mpi4py.__version__)'
python -c 'import tensorflow; print(tensorflow.__version__)'
```
* The sample code is tested and works on two systems that have following versions.
```
python: 3.7.0
numpy: 1.16.3
mpi4py: 3.0.0
tensorflow: 1.13.1
```
```
python: 3.5.2
numpy: 1.16.4
mpi4py: 3.0.2
tensorflow: 1.14.0
```

## Sample comparison of Anytime and Fixed mini-batch (AMB and FMB)
* In this section
   * [`run_perf_amb.py`](src/run_perf_amb.py): generates data (see therewithin the applicable arguments).
   * [`plot_perf_amb.py`](src/plot_perf_amb.py): plots data (see below for a sample).
* m3.xlarge instances in Amazon EC2
* Hub-and-spoke - 10 nodes and master
* CIFAR10 dataset
* Induced stragglers
* RMS-prop optimizer
* Generated with following arguments for `run_perf_amb.py`:
    * `cifar10 fmb rms 242 --test_size 100 --induce --decay_rate 0.93`
    * `cifar10 amb rms 356 --amb_time_limit 6.2 --amb_num_partitions 16 --test_size 100  --induce --decay_rate 0.93`

<img src="data/800_cifar10/set2/all_plots.png?raw=true"/>

* See more samples in [`data`](data).

## Instructions for running on Amazon EC2
* Create an MPI cluster - [StarCluster](http://star.mit.edu/cluster/docs/latest/installation.html) may be helpful.
* Sample commands:
``` shell
mpi1 python -u run_perf_amb.py mnist fmb rms 64
mpi4 python -u run_perf_amb.py mnist amb adm 64 --amb_time_limit 9.2 --amb_num_partitions 64 --starter_learning_rate 0.001
mpi4 python -u run_perf_amb.py cifar10 amb adm 64 --amb_time_limit 9.2 --amb_num_partitions 64 --starter_learning_rate 0.001 --test_size 100
mpi4 python -u run_perf_amb.py mnist amb rms 4096 --amb_time_limit 9.2 --amb_num_partitions 64 --starter_learning_rate 0.001 --induce
mpiall python -u run_perf_amb.py mnist amb rms 1024 --amb_time_limit 1.9 --amb_num_partitions 16
mpi11 python -u run_perf_amb.py cifar10 amb rms 256 --amb_time_limit 5.5 --amb_num_partitions 16 --test_size 100 --induce > $SCRATCH/anytime/output_amb 2>&1
mpi11 python -u run_perf_amb.py cifar10 fmb rms 256 --test_size 100 --induce > $SCRATCH/anytime/output_fmb 2>&1
```
* Here, `mpi1`, `mpi4` and `mpiall` are aliases. For example `mpi4` translates to `mpirun -host master,node001,node002,node003`.
* If running on Niagara use `srun -n 1` in place of `mpi1`.
* For CIFAR10 it is important to set a low value for `test_size`. Otherwise master will use all 10,000 samples in the test dataset to evaluate the model. As a result workers will have to wait to send updates to the master.
* A sample log line printed by a worker looks like `Sending [256] examples, compute_time [5.63961], last_idle [0.267534], last_send [0.244859]`.
    * `sleep_time`: time spent sleeping in the current step if `induce` is true (inducing stragglers).
    * `last_send`: in the last step, time spent sending the update to the master.
    * `last_idle`: in the last step, time spent after sending an update till starting computations for the next step (includes receiving time from the master as well).
* Generate all plots using `python plot_perf_amb.py --short_label --save --silent --fraction 0.72`. Training loss plot is generated by the loss evaluated at the master in each step using a `batch_size` minibatch.
* Point to a specific directory and a datset, and plot only a subset of plots using `python plot_perf_amb.py --short_label --data_dir ~/SCRATCH/distributed --dir_regex cifar* --type all_plots --subset accuracy_vs_time loss_vs_step`.

## Stats on EC2
Commands and sample worker outputs:
* `mpi11 python -u run_perf_amb.py cifar10 fmb rms 512 --test_size 100`:
``` shell
wk10|Sending [512] examples, compute_time [11.353], last_idle [0.297866], last_send [0.271033]
wk4|Sending [512] examples, compute_time [11.3975], last_idle [0.278468], last_send [0.255518]
wk0|step = 9, loss = 4.4926357, learning_rate = 0.001, accuracy = 0.13 (11.885 sec)
```
* `mpi11 python -u run_perf_amb.py cifar10 amb rms 512 --amb_time_limit 11 --amb_num_partitions 16 --test_size 100`:
``` shell
wk8|Sending [512] examples, compute_time [11.485], last_idle [0.765861], last_send [0.25578]
wk4|Sending [512] examples, compute_time [11.4716], last_idle [0.777958], last_send [0.247732]
wk0|loss = 3.5509295, learning_rate = 0.001, step = 20, accuracy = 0.09 (12.469 sec)
```
* `mpi11 python -u run_perf_amb.py cifar10 fmb rms 256 --test_size 100`
```
wk4|Sending [256] examples, compute_time [5.64347], last_idle [0.241176], last_send [0.221801]
wk8|Sending [256] examples, compute_time [5.66594], last_idle [0.258161], last_send [0.421286]
wk0|step = 109, loss = 2.3923714, learning_rate = 0.001, accuracy = 0.13 (6.153 sec)
```
* `mpi11 python -u run_perf_amb.py cifar10 amb rms 256 --amb_time_limit 5.0 --amb_num_partitions 8 --test_size 100`
```
wk5|Sending [256] examples, compute_time [5.69975], last_idle [0.257738], last_send [0.347983]
wk3|Sending [256] examples, compute_time [5.71114], last_idle [0.250323], last_send [0.344623]
wk0|step = 129, learning_rate = 0.001, loss = 2.265991, accuracy = 0.15 (6.426 sec)
```


### Effect of partitioning minibatches using `tf.while_loop`
* AMB implementation in this code uses `tf.while_loop` to partition minibatches.
* The input minibatch is partitioned into `amb_num_partitions` 'micro' batches, each of size `batch_size/amb_num_partitions`. The gradients of partitions are then calculated in a loop, starting from the first while the elapsed time>`amb_time_limit`. When the condition fails the worker sends the gradients (summed across the processed partitions) to master.
* The execution speed for `amb_num_partitions=10` is lower than that for `amb_num_partitions=1` even for the same `batch_size`. Can measure execution speed drop on different platforms (EC2, Compute Canada), NN architectures (fully-connected, convolutional).
* Following plots are produced using [`test_perf_partitions.py`](src/test_perf_partitions.py) which includes data generating and plotting commands.
* The CIFAR10 model used in this code produces following output on EC2.
    * Number of partitions: `amb_num_partitions`
    * Partition size: `batch_size`/`amb_num_partitions`
    * Time per step: Time taken to go through all the partitions (covering the whole batch)
    * Time per sample: Time per step divided by batch size
<img src="data/1000_test_perf_partitions/ec2-m3-xlarge_cifar10.png?raw=true"/>

* Conclusion: For CIFAR10, if `batch_size` > 512, maintaining a partition size > 32 (2^5) will cause a minimal impact on the execution time.
* This means for `batch_size`=512 set `amb_num_partitions`=512/32=16.
* Below is another example for fully connected (top) vs convolutional (bottom) network for a toy dataset. Note that the while loop has a lower impact for convolutional nets. This is because the matrix multiplication in fully connected nets is well supported in modern hardware.
* See more in [`data/1000_test_perf_partitions`](data/1000_test_perf_partitions).

<img src="data/1000_test_perf_partitions/ec2-t2-micro_toy_model_fc.png?raw=true"/>
<img src="data/1000_test_perf_partitions/ec2-t2-micro_toy_model_conv.png?raw=true"/>

* Sample commands:
``` shell
python -u test_perf_partitions.py eval mnist --batch_size 64 --num_partitions 2
python -u test_perf_partitions.py eval cifar10 --batch_size 64 --num_partitions 2
python -u test_perf_partitions.py batch toy_model
python -u test_perf_partitions.py plot --save --silent --ext png pdf
```


### Impact of AMB on batch normalization
* See plots in [`data/1100_batchnorm_impact_AMB`](`data/1100_batchnorm_impact_AMB`).
* When `amb_num_partitions=1` AMB has same performance as FMB. When `amb_num_partitions` increasese the performance decreases.


### Communication overhead vs. number of workers
* Modify and run [`test_bandwidth.sh`](test_bandwidth.sh) to generate data.
* Use command `python plot_perf_amb.py --type master_bandwidth --dir_name test_bandwidth/4_reduce_arr/bandwidth__1024 --dir_regex b*` to plot the results.
