Usage Guide
===========

The EDAI shell intelligently routes every line you type to the right
handler: Tcl commands go to the Tcl interpreter, Python code goes to
IPython, and everything else goes to the LLM agent.

Direct Tcl Commands
-------------------

Type any supported Tcl command directly. No ``%tcl`` prefix needed.

.. code-block:: text

    In [1]: read_liberty -path /libs/slow.lib
    [simulated] Data loaded successfully.

    In [2]: read_sdc -path /constraints/top.sdc
    [simulated] Constraints loaded successfully.

    In [3]: run_placer -max_density 0.75 -max_util 0.8
    [simulated] Placement completed. Overflow: 2.3%

Tcl commands support variable substitution:

.. code-block:: text

    In [4]: set lib_path /libs/slow.lib
    /libs/slow.lib

    In [5]: read_liberty -path $lib_path
    [simulated] Data loaded successfully.

And command substitution:

.. code-block:: text

    In [6]: puts [set lib_path]
    /libs/slow.lib

Python Commands
---------------

Any valid Python code is executed directly:

.. code-block:: text

    In [7]: slack = -0.23

    In [8]: print(f"Worst slack: {slack}")
    Worst slack: -0.23

    In [9]: import math
    In [10]: math.sqrt(4)
    Out[10]: 2.0

Natural Language (LLM Agent)
----------------------------

When your input is neither a known Tcl command nor valid Python, it
is sent to the LLM agent. The agent interprets your intent and
responds with the appropriate EDA commands.

.. code-block:: text

    In [11]: set up the design with liberty and LEF files, then run
              placement with max density 0.7
    >> Agent: I'll help you set up and run placement.
    >> Running: read_liberty -path ./lib/slow.lib
    >> Running: tech_lef_init -path ./lef/tech.lef
    >> Running: run_placer -max_density 0.7
    [simulated] Placement completed. Overflow: 1.8%

The agent remembers conversation context:

.. code-block:: text

    In [12]: what was the overflow from the last placement?
    >> The overflow after placement was 1.8%.

Using the %tcl Magic
--------------------

You can also use the explicit ``%tcl`` IPython magic command:

.. code-block:: text

    In [13]: %tcl read_liberty -path ./lib/slow.lib
    [simulated] Data loaded successfully.

This is useful when you need to explicitly mark a command as Tcl,
or when using Tcl from within Python code cells.

The ask_agent() Function
------------------------

You can programmatically send messages to the LLM agent from Python
code:

.. code-block:: text

    In [14]: result = ask_agent("check if setup timing is met")
    >> Running: run_sta
    >> Running: report_timing -path_type max
    [simulated] Setup slack: 0.05ns — timing is met.

    In [15]: print(result)
    Setup slack: 0.05ns — timing is met.

The run_tcl() Function
----------------------

Execute Tcl commands from Python code:

.. code-block:: text

    In [16]: run_tcl("read_liberty -path ./lib/slow.lib")
    [simulated] Data loaded successfully.

This is useful when writing Python scripts that mix EDA commands
with analysis logic.

Running a Typical Flow
----------------------

Here is an example of a complete design flow in EDAI:

.. code-block:: text

    # 1. Initialize the flow
    flow_init
    db_init

    # 2. Load design data
    read_liberty -path ./lib/slow.lib
    read_liberty -path ./lib/fast.lib
    tech_lef_init -path ./lef/tech.lef
    def_init -path ./input/top.def
    verilog_init -path ./input/top.v

    # 3. Floorplan and power delivery
    floorplan_init -util 0.7 -aspect 1.0
    create_grid -layer M1 -width 0.2 -spacing 1.0
    create_stripe -layer M2 -width 0.5 -spacing 5.0

    # 4. Placement
    run_placer -max_density 0.75

    # 5. Clock tree
    run_cts

    # 6. Routing
    run_rt

    # 7. Timing and power
    run_sta
    report_timing -path_type max
    run_power
    report_power

    # 8. Save results
    def_save -path ./output/top.def
    netlist_save -path ./output/top.v
