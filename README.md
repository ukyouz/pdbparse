# pdbparse

This project is inspired by [moyix/pdbparse](https://github.com/moyix/pdbparse)

## Improvements

I made low-level python structures closer to pdb's original format. Also, since parsing may be slow, so this project allows user to dump/load the parsed result as a binary file with python pickle module.

## What is this for?

PDBparse is a GPL-licensed library for parsing Microsoft PDB files. Support for these is already available within Windows through the Debug Interface Access API, however, this interface is not usable on other operating systems.

PDB files are arranged into streams, each of which contains a specific bit of debug information; for example, stream 1 contains general information on the PDB file, and stream 2 contains information on data structures.

Currently, there is support for Microsoft PDB version 7 files (Vista and most Windows XP symbols). The following streams are currently supported:

* Root Stream
* Info Stream
* Type Stream
* Debug Info Stream
* Global Symbol Stream
* OMAP Streams
* Section Header Streams

## Requirements

The open-source library [Construct](http://construct.wikispaces.com/) is used to perform the low-level parsing, and is required to run the code. 
