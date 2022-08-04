# memorizer-data
Our experiences with memorizer

## Installation
The installation of a kernel with memorizer in it (Linux 5.15.15) consists of only a few steps. The best way to install is to do it through the gitlab (https://gitlab.com/fierce-lab/linux). The steps are under [Quick Start](https://gitlab.com/fierce-lab/linux/-/blob/v5.15.15-memorizer-dev/README.md#quick-start) in the readme at the base level of the repository. 

### Docker progress
There are a few things to note about the docker installation. My partner, Noah, experienced quite a few issues with trying to run memorizer in a docker container, since there seem to be a few unresolved issues in the docker script that is given here (https://github.com/linuxkit/linuxkit/blob/master/projects/memorizer/kernel-memorizer/Dockerfile). We are working on getting this fixed.
Note from Noah: So the main issue with the Docker container is that the memorizer is baked into a custom linux kernel. This means that to Dockerize the memorizer, you would have to create a custom base image using a compiled version of the memorizer kernel. I ran into several issues trying to get the Docker container to work to no avail so my recommendation is to continue using a QEMU instance to run the memorizer as that will save you the headache of Docker. If you DO choose to create a Docker container for the memorizer, then the first steps would be to figure out how to create a custom base image from the memorizer kernel and go from there.

## Running memorizer
The first thing to note is that there needs to be a slight modification in the `./scripts/memorizer/run_qemu.sh` file: the keyword `memalloc=$MEM_MEMORIZER...` should instead be `memalloc_size=[some constant]`. This change is what allows the memorizer to have more than the default amount of memory allocated, without which the user might experience quite a few kernel panics due to memorizer running out of memory. Another change to that script if running the QEMU instance inside of a VM is to add `pmu=off` to `host`, making the line `host,pmu=off`. Now why exactly this fixes some issues with QEMU inside a VM? Not sure but it'll save you a headache. Now that the script is fixed, you can follow the quick start guide found above. If running the QEMU instance of memorizer inside a VM, remember to have KVM enabled for the VM otherwise QEMU will not boot.

### Memorizer Fields
The memorizer fields on the actual github are a tad outdated. After scrounging through some of the code I was able to put this together for the KMAP outputs:
Objects: alloc_ip,alloc_pid,va,size,alloc_time,free_time,free_ip,allocator,process,slab_cache
	Subjects: instr_ip,writes,reads

Objects:
	alloc_ip - ip (instruction pointer) that allocated the object 
	alloc_pid - PID that allocated the object
	va - virtual address of the object
	size - how large (in bytes?) of an allocation
	alloc_time - time (in jiffies) that the object was allocated in memory
	free_time - time (in jiffies) that the object was freed from memory
	free_ip - ip that freed the object
	allocator - type of allocation (SLAB, kmalloc, malloc)
	process - process name in human-readable form
	slab_cache - type of slab cache used to allocated this object
Subjects:
	instr_ip - ip that read/write from this object
	writes - number of writes
	reads - number of reads

### Useful commands:
Please check the [scripts](scripts/) folder for the scripts we have written so far.

#### Bash script (simple, not as robust):
A simple bash script, using this we avoid executing memorizer enable, disable, and clear commands manually. As an input, it takes the test suite which needs to be executed in the linux test project, and it outputs a kmap file with the memorizer output for the given test. Note that the CLI output can be piped to a file, which can serve as a way to log the test results. 

#### Python script (complex, robust test using the linux test project):
We created a Python script to work in tandem with the Linux Test Project. Simply run the script in the folder where you wish for it to place the Kmaps (CAPMAPS, whatever you wish to call them) and give it the path to the ./ltp directory and it will begin running the ltp tests while creating kmaps. It has a few helpful flags for the testing process:
    -t, --tests: the group of LTP tests that you wish to run
    -o, --omit: the group of LTP tests that you wish not to run but will run all others 
    -p, --path: the path to the ./ltp directory (NECESSARY TO RUN SCRIPT)
    -g, --granularity: the number of tests to run before producing a kmap (default=1)
    -r, --random: randomizes the test order. makes more sense for larger granularities
    -n, --number: total number of tests to run before exiting the script
Hopefully this script makes your life easier when collcting data using LTP.

### Analyzing Memorizer Output:
As you may have noticed, the memorizer provides a whole wealth of data that can be hard for the human eye to analyze by itself. That is why we have taken a couple of directions to create ways to make this data more digestable. The first tool is that we have created a python script that takes in a kmap and creates a force-directed graph of the kmap. Nodes represent unique instruction pointers which are some kind of alloc_ip (red) or some kind of read/write operation (blue). The edges between these nodes are always reads/write nodes that read/write on a certain allocated object. The other analysis tool that we have been working on is utilizing a GNN (graph neural network) to see if we can identify malicious programs within it, though it is cuurrently in a primitive state and needs some improvement.

### GNNs - A start
Check out a custom GNN-esque Machine Learning implementation [here](kmapGraph.py). Also works: try to fit the kmap data to an open-source GNN implementation (however we were not very successful with this, hence the custum GNN implementation.

## Next steps
Reading the kmap files that are in the [kmaps](kmaps/) folder: https://gitlab.com/fierce-lab/memorizer/-/blob/master/src/post-analysis/CAPMAP.py
Other applications are currently being discussed.

### Other tools
We have also explored other tools, such as Volatility. Currently, our progress has been in using the tool, and we have explored ways of how we can use volatility as a way to check what the memorizer outputs, however this has not been thoroughly explored.
