Overview
========

What is EDAI?
-------------

EDAI is a terminal-based interactive environment that bridges the gap
between natural language and EDA (Electronic Design Automation) tools.
It provides an IPython shell augmented with:

* A **large language model agent** that understands your design intent
  and translates it into executable EDA commands.
* A **built-in Tcl interpreter** that understands 180+ EDA commands
  across subsystems such as floorplanning, placement, CTS, routing,
  STA, power analysis, DRC, and more.
* A **simulation backend** that lets you explore the full workflow
  without requiring an actual EDA license or tool installation.

EDAI is designed for digital chip design workflows where engineers
need to quickly prototype flows, experiment with tool settings, or
learn an EDA toolchain through conversational interaction.

How it Works
------------

When you start EDAI, you enter an IPython shell with three input
modes, automatically detected:

**Tcl commands**
    If your input looks like a valid EDA Tcl command
    (e.g., ``read_liberty -path ./lib.lib``), it is routed directly
    to the built-in Tcl interpreter for execution.

**Python code**
    If your input can be parsed as valid Python
    (e.g., ``print(sta.worst_slack)``), it is executed in the IPython
    namespace and the result is displayed.

**Natural language**
    Everything else is sent to the LLM agent, which interprets
    your intent, selects the appropriate Tcl command, and returns the
    result.

This triage happens automatically on every line, so you can mix all
three styles freely in a single session.

Target Audience
---------------

* **Digital design engineers** running RTL-to-GDS flows.
* **EDA tool application engineers** developing and debugging
  tool scripts.
* **Students and researchers** learning EDA toolchains through
  conversational interaction.
* **Flow automation engineers** prototyping new design flows
  quickly.
