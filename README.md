# memorizer-data
Our experiences with memorizer

## Installation
The installation of a kernel with memorizer in it (Linux 5.15.15) consists of only a few steps. The best way to install is to do it through the gitlab (https://gitlab.com/fierce-lab/linux). The steps are under [Quick Start](https://gitlab.com/fierce-lab/linux/-/blob/v5.15.15-memorizer-dev/README.md#quick-start) in the readme at the base level of the repository. 

### Docker progress
There are a few things to note about the docker installation. My partner, Noah, experienced quite a few issues with trying to run memorizer in a docker container, since there seem to be a few unresolved issues in the docker script that is given here (https://github.com/linuxkit/linuxkit/blob/master/projects/memorizer/kernel-memorizer/Dockerfile). We are working on getting this fixed, [@Noah post your docker edit link here].

## Running memorizer
The first thing to note is that there needs to be a slight modification in the `./scripts/memorizer/run_qemu.sh` file: the keyword `memalloc=$MEM_MEMORIZER...` should instead be `memalloc_size=[some constant]`. This change is what allows the memorizer to have more than the default amount of memory allocated, without which the user might experience quite a few kernel panics due to memorizer running out of memory.

### Useful commands:
Please check the [scripts](scripts/) folder for the scripts we have written so far.

#### Bash script (simple, not as robust):
A simple bash script, using this we avoid executing memorizer enable, disable, and clear commands manually. As an input, it takes the test suite which needs to be executed in the linux test project, and it outputs a kmap file with the memorizer output for the given test. Note that the CLI output can be piped to a file, which can serve as a way to log the test results. 

#### Python script (complex, robust test using the linux test project):
@Noah this section is all yours

## Next steps
Reading the kmap files that are in the [kmaps](kmaps/) folder: https://gitlab.com/fierce-lab/memorizer/-/blob/master/src/post-analysis/CAPMAP.py
Other applications are currently being discussed.

### Other tools
We have also explored other tools, such as Volatility. Currently, our progress has been in using the tool, and we have explored ways of how we can use volatility as a way to check what the memorizer outputs, however this has not been thoroughly explored.
