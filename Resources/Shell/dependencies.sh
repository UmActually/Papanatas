#!/bin/sh

mkdir vendor
cd vendor
export PATH=$(pwd):$PATH

# Download FFmpeg
curl "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" -L --silent --fail --retry 5 --retry-max-time 15 -o "ffmpeg.tar.xz"

# Unpack tar
tar -xJf "ffmpeg.tar.xz" --strip-components=1
rm "ffmpeg.tar.xz"

# Download YTDL
curl "https://yt-dl.org/downloads/latest/youtube-dl" -L --silent --fail --retry 5 --retry-max-time 15 -o "youtube-dl"

# Set executable
chmod a+rx "youtube-dl"
cd ..
