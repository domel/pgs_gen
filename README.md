
# PG-Schema to Cypher Generator

This repository contains a Python script that reads a **PG-Schema** definition from a file and optionally a CSV file specifying the number of nodes and edges to generate for each label. The script produces `CREATE` statements in Cypher, allowing you to quickly seed a graph database such as Neo4j with synthetic data.

## Overview

1. **Reads the PG-Schema** from a file (e.g., `Enterprise_Graph.pgs`) containing definitions of nodes and relationships in the property-graph style.
2. **Parses** the schema to extract:
   - Node types and their properties.
   - Relationship types and the labels of their start and end nodes.
3. **Generates Cypher** statements to create a desired number of nodes and relationships.  
   - You can specify global default values (`-n` for nodes and `-e` for edges) or fine-tune values on a per-label basis via an optional CSV file (`-c`).
4. **Outputs** the Cypher `CREATE` statements to standard output, which you can directly use (or redirect to a `.cypher` file) and load into a Neo4j database or any other system that supports Cypher.

## Script Usage

```bash
python pgs_gen.py <PG-Schema file> [options]
```

### Required Argument

- `<PG-Schema file>`: Path to the file containing the PG-Schema definition.  
  Typically, this file includes definitions similar to:
  ```
  CREATE GRAPH TYPE EnterpriseGraph STRICT {
    (EmployeeType: Employee {name STRING, employee_id INT}),
    (DepartmentType: Department {name STRING, department_id INT}),
    ...
    (:EmployeeType)-[WorksInType: worksIn]->(:DepartmentType),
    ...
  }
  ```

### Optional Arguments

- `-n, --nodes` `<int>`  
  Sets the **default** number of nodes to create for **each** node label (if not specified in the CSV).  
  Default value: `4` (if not provided).

- `-e, --edges` `<int>`  
  Sets the **default** number of edges (relationships) to create for **each** relationship label (if not specified in the CSV).  
  Default value: `4` (if not provided).

- `-c, --csv` `<path>`  
  Specifies a CSV file with rows of the form `<label_name>,<count>`.  
  - **label_name**: the internal node label or relationship label as defined in the PG-Schema.  
  - **count**: the number of nodes or edges to generate for that label.

  When present, any label in this CSV will override the default values set by `-n` or `-e`. Labels not listed in the CSV use the default values or 4 if none are supplied.

## Example Files

### Sample `Enterprise_Graph.pgs`

```sql
CREATE GRAPH TYPE EnterpriseGraph STRICT {
  (EmployeeType: Employee {name STRING, employee_id INT}),
  (DepartmentType: Department {name STRING, department_id INT}),
  ...
  (:EmployeeType)-[WorksInType: worksIn]->(:DepartmentType),
  (:EmployeeType)-[ManagesType: manages]->(:DepartmentType),
  ...
}
```

### Sample `eg.csv`

```
EmployeeType,50
DepartmentType,10
WorksInType,20
ManagesType,5
```

In this CSV:
- `EmployeeType` will have 50 nodes generated.
- `DepartmentType` will have 10 nodes.
- The `worksIn` relationship (internal label `WorksInType`) will have 20 edges.
- The `manages` relationship (internal label `ManagesType`) will have 5 edges.

All other labels in the PG-Schema not listed in this CSV will revert to the default value (either from `-n, -e` or 4 if not specified).

## How to Run

1. **Install Dependencies**  
   This script uses only standard Python libraries (`argparse`, `csv`, `os`, etc.), so no additional installation steps are required.

2. **Make the Script Executable** (optional, on Unix-like systems):  
   ```bash
   chmod +x pgs_gen.py
   ```

3. **Run the Script**  

   - **Without CSV** (use `-n` and `-e` as defaults):
     ```bash
     python pgs_gen.py Enterprise_Graph.pgs -n 10 -e 5
     ```
     This command will:
     - Parse `Enterprise_Graph.pgs`,
     - Generate 10 nodes for each defined node label,
     - Generate 5 edges for each defined relationship label.

   - **With CSV**:
     ```bash
     python pgs_gen.py Enterprise_Graph.pgs -c eg.csv
     ```
     Here, any label found in `eg.csv` will use its specified count. All other labels revert to the default of 4 (unless overridden by `-n` or `-e`).

   - **Combination**:
     ```bash
     python pgs_gen.py Enterprise_Graph.pgs -c eg.csv -n 8 -e 6
     ```
     In this scenario:
     - Labels present in `eg.csv` use values from the CSV,
     - Labels not listed in `eg.csv` will have 8 nodes (if they are node labels) or 6 edges (if they are relationship labels).

4. **Redirecting Output**  
   If you want to save the output to a file:
   ```bash
   python pgs_gen.py Enterprise_Graph.pgs -n 10 -e 5 > load.cypher
   ```
   Then you can open and inspect `load.cypher`, or directly load it into your Neo4j environment.

## Sample Output

After generating, you should see output in the console similar to:

```
-- Cypher CREATE statements for nodes --
CREATE (EmployeeType_0:Employee { name: 'UUHXKWPE', employee_id: 527 });
CREATE (EmployeeType_1:Employee { name: 'JDTQIWQL', employee_id: 39 });
...

-- Cypher CREATE statements for relationships --
CREATE (EmployeeType_0)-[:worksIn]->(DepartmentType_1);
CREATE (EmployeeType_2)-[:manages]->(DepartmentType_3);
...
```

You can copy and paste these statements into a Neo4j Browser or use the Neo4j command line to import them.

## Notes / Limitations

1. **Primitive Data Generation**: Properties such as `STRING` and `INT` are populated with simplistic, random values. If you want more realistic data (e.g., names, addresses), you can integrate libraries like [Faker](https://faker.readthedocs.io/en/master/).
2. **Self-Loops**: The script avoids creating an edge `(node)->(node)`, but all other random pairings are allowed. You may see multiple edges between the same nodes if they appear in the sample or if you run at high relationship counts.
3. **Schema Complexity**: This parser is simplistic and relies on specific format patterns. If your PG-Schema has advanced features or a different format, the script may need further customization.

---

**License**: MIT
