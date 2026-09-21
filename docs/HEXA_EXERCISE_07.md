# Exercise 07: reproducible flight-simulation evidence

Status: **ANALYSIS_ONLY / NOT_FOR_PROCUREMENT**

This exercise implements the FLIGHT-SIM-04 evidence gate. It combines the
nominal takeoff-hover-land result and the command-dropout controlled-landing
result into one machine-readable manifest.

Each scenario result records stable identifiers for the Gazebo model,
velocity controller, scenario, and (where used) command guard. The manifest
also records the Git revision, whether the working tree is clean, SHA-256
digests of the model, world, controller, guard, scenario sources, both result
files, their criteria, and their quantitative metrics.

After running both dynamic scenarios, build the manifest with:

    ros2 run arachne_hx6_control flight_evidence \
      --repository-root "$PWD" \
      --nominal /tmp/arachne_gazebo_flight.json \
      --link-loss /tmp/arachne_gazebo_link_loss.json \
      --output /tmp/arachne_flight_evidence.json

The command fails if either scenario failed, if required metrics or criteria
are absent, or if any planning boundary is weakened. A passing manifest means
the two simulation records are internally complete and traceable to their
sources. It does not validate hardware, authorize procurement, or establish
physical flight readiness.
