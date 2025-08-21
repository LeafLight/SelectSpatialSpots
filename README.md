---
title: SSS for Select Spatial Spots
tags: ["Spatial Transcriptome", "Bioinformatics", "Data Analysis"]
date: 2025-08-22 01:00:50
---
# Abstract
It is a _____Dash__ app for Spatial Transcriptome Analysis, especially the part of selecting spots of interest interactively. You can get a spots assignment csv for downstream analysis.

# Quick Start

- clone this repository
- install the requirements
```bash
pip install requirements
```
- prepare your csv and image(optional, and smaller for faster)
    - csv colnames: `CELL_ID`, `X`, `Y`
    - image: no larger than 5mb for faster processing, this app is just for spots selecting and you can add image with higher resolution laterly.

- Align Your Image with `X`, `Y`, `Scale` on the left
- Select the color and enter the group name you want to use
- Select Spots with lasso(with your mouse holded on) _____after__ activating the corresponding group
- Export the assignment csv
- 
