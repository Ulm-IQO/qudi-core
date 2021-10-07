---
layout: default
title: qudi-core
---

[back](index.md)

---

# How to get started with qudi
This article is an attempt at guiding new users through the process of installing, understanding 
and using qudi.

## Installation
If you are new to qudi, you may want to try it out in a demo environment on your own computer first.

Luckily, the way qudi is built lets you have a look at most user interfaces and tools even if your 
computer isn't connected to real instrumentation hardware.\
For every hardware interface in qudi, there must be a dummy module to simulate this hardware type 
in the absence of a real instrument.

The installation however is always the same. You can refer to the detailed step-by-step 
[installation guide](setup/installation.md) to install qudi.

## Startup
Time to fire up the engines...

Please refer to the detailed [startup guide](setup/startup.md) to run qudi.

If you have set up everything correctly, you should see the main window of qudi coming up.

## Playtime
Qudi should now run with only dummy hardware modules configured. That means you can load any 
toolchain you like by clicking on the respective GUI module name in the main window without 
breaking anything.

So... feel free to play around and get familiar with some of the GUIs and the main manager window.

Close qudi if you had enough by selecting `File -> Quit qudi` in the top left menu bar of the 
manager window. Alternatively you can also press the shortcut `Ctrl + Q` while the manager window 
is selected.

## Configuration
If you want to use qudi productively in your setup, we have to get rid of all the dummy modules and 
replace them with real hardware modules.\
You probably also want to get rid of some toolchains (GUI/logic/hardware) entirely if you are not 
using them in your specific setup. They will just clutter you manager GUI otherwise.

For telling qudi what modules to use and how they should connect to each other, you need to provide
a setup-specific config file. 

Please refer to the detailed [configuration guide](setup/configuration.md) to set up a proper qudi 
config for your needs.

## \>\>\> To Be Continued... \<\<\<

## Then what ?

You might be lucky enough to find all the tools you need to conduct you experiment. But there's a 
good chance you will need something that haven't been developed before. 

This may be just a hardware module to control a new instrument, a new button in a GUI or a whole 
new hardware/logic/GUI toolchain.

In that case, you will need to go even deeper in the code. But fret not... we have set up a few 
[programming guidelines](programming_guidelin) and even template modules to get you started.

There is no need to delve into the very core of qudi to understand its entirety before implementing new measurement modules.

You may even want to share your hard work with others or find people who can give you input on the 
matter. Please refer to our [contributing guideline](programming_guidelines/contributing.md).
 
---

[back](index.md)
