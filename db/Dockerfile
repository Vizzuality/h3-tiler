FROM postgis/postgis:16-3.4

LABEL maintainer="Vizzuality <hello@vizzuality.com>"

RUN apt-get update

RUN apt-get install -y pgxnclient wget make gcc libtool git postgresql-client-16 postgresql-server-dev-16

# Install latest version of cmake, not available in apt
RUN cd /opt && \
    mkdir cmake && \
    wget https://github.com/Kitware/CMake/releases/download/v3.27.6/cmake-3.27.6-linux-x86_64.sh && \
    chmod +x cmake-3.27.6-linux-x86_64.sh && \
    ./cmake-3.27.6-linux-x86_64.sh --skip-license --prefix=/opt/cmake --exclude-subdir && \
    rm cmake-3.27.6-linux-x86_64.sh && \
    ln -s /opt/cmake/bin/* /usr/local/bin/

RUN pgxn install h3==4.1.3

COPY entrypoint.sh /usr/local/bin/

ENTRYPOINT ["entrypoint.sh"]
