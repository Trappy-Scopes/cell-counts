# cell-counts

Cell counting database and auto-plotting repository.





## Control Idioms

+ All data files must be added to the `datafile` directory.
+ `filelogs.yml` must not be modified by a human user. It is only inteneded to be used by GitHub Actions.
+ Excel sheet name with an asterisk (*****) will be ignored.



## Control Flow

```mermaid
flowchart LR
	files["to_process<br>(files)"] --> extract_sheets --for_all_sheets--> extract-data --> plot
```



## Usual Cell Counting and Plotting



```mermaid
graph LR
	new-counting("new-counting<br>(create from template)") --> user-adds-data --> analysis
```

```mermaid
---
title: analysis
---
graph LR

data((data)) --> load-to-dataframe --> calculate-other-stats --save-->load-to-dataframe
calculate-other-stats --> convert-counts-to-per-mL --> plot-raw --> plot-fits --> calculate-doubling-time 
	
```

