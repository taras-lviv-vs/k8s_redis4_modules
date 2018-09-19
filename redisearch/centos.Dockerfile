FROM centos:7

RUN yum update -y && \
	yum install epel-release -y && \
	yum install redis sed bash gcc gcc-c++ cmake3 make git -y && \
	# Remove all entries for currently enabled repositories from the cache
	git clone https://github.com/RedisLabsModules/RediSearch.git && \
	cd RediSearch && mkdir build && cd build && cmake3 .. -DCMAKE_BUILD_TYPE=RelWithDebInfo && make && \
	yum erase git make cmake3 gcc-c++ gcc -y && \
	yum clean all && \
	rm -rf /var/cache/yum

# TODO: install/build redis4

