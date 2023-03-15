# Introduction

With Matcha, you'll be up and running with an open source MLOPs environment in Azure, in 10 minutes.

# Getting started

## Set up your environment

```
git clone git@github.com:fuzzylabs/matcha-example.git
```

First, install Matcha with PIP:

```
pip install matcha
```

Then, authenticate with Azure:

```
az login
```

And provision your base environment:

```
# sets up the basic env with sensible defaults
matcha provision
```

## Run an example training workflow

```
cd recommender
```

```
matcha run train deploy
```

Verify that it works

```
matcha verify
```
