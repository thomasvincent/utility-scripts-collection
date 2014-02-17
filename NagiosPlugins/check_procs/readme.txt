RANGEs are specified 'min:max' or 'min:' or ':max' (or 'max'). If
specified 'max:min', a warning status will be generated if the
count is inside the specified range

This plugin checks the number of currently running processes and
generates WARNING or CRITICAL states if the process count is outside
the specified threshold ranges. The process count can be filtered by
process owner, parent process PID, current state (e.g., 'Z'), or may
be the total number of running processes


- 24.02.2012