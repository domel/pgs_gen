#!/usr/bin/env python3

import sys
import re
import random
import string
import argparse
import csv
import os

def generate_random_string(length=8):
    """Helper function that generates a random string of uppercase letters."""
    return ''.join(random.choices(string.ascii_uppercase, k=length))

def generate_random_int(min_val=1, max_val=1000):
    """Helper function that generates a random integer within the given range."""
    return random.randint(min_val, max_val)

def parse_pg_schema(schema_text):
    """
    Parses the PG-Schema text and returns:

    1) nodes_dict – a dictionary of the form:
       {
         'InternalLabelName': {
             'external_label': 'ExternalLabelName',
             'properties': [(property_name, property_type), ...]
         },
         ...
       }

    2) relationships_list – a list of tuples in the format:
       (rel_internal_label, start_internal_label, end_internal_label, rel_external_label)
    """
    # Regex matching a node, e.g. (PostType: Post {name STRING, post_id INT})
    node_pattern = re.compile(
        r'\(\s*(\w+)\s*:\s*(\w+)\s*\{\s*([^}]*)\s*}\s*\)'
    )
    # Regex matching a relationship, e.g. (:PostType)-[IsLocatedInPostType: isLocatedIn]->(:PlaceType)
    relationship_pattern = re.compile(
        r'\(\s*:\s*(\w+)\s*\)\s*-\[\s*(\w+)\s*:\s*(\w+)\s*\]->\(\s*:\s*(\w+)\s*\)'
    )

    nodes_dict = {}
    relationships_list = []

    lines = schema_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if the line defines a node
        node_match = node_pattern.search(line)
        if node_match:
            internal_label, external_label, properties_str = node_match.groups()
            properties = []
            if properties_str.strip():
                # e.g. "name STRING, post_id INT"
                prop_pairs = [p.strip() for p in properties_str.split(',')]
                for pair in prop_pairs:
                    parts = pair.split()
                    if len(parts) >= 2:
                        prop_name = parts[0].strip()
                        prop_type = parts[1].strip()
                        properties.append((prop_name, prop_type))
            nodes_dict[internal_label] = {
                'external_label': external_label,
                'properties': properties
            }

        # Check if the line defines a relationship
        rel_match = relationship_pattern.search(line)
        if rel_match:
            start_label, internal_rel_label, external_rel_label, end_label = rel_match.groups()
            relationships_list.append((internal_rel_label, start_label, end_label, external_rel_label))

    return nodes_dict, relationships_list

def generate_cypher_for_nodes(nodes_dict, counts_map, default_count=4):
    """
    Generates Cypher CREATE statements for nodes.
    - nodes_dict: a dictionary describing nodes (returned by parse_pg_schema).
    - counts_map: a dictionary that may store the number of nodes for the key = internal label.
    - default_count: default number of nodes if there is no entry in counts_map.

    Returns:
    - statements: a list of Cypher CREATE statements
    - node_ids: a dictionary {internal_label_name: [node_identifiers], ...}
    """
    statements = []
    node_ids = {label: [] for label in nodes_dict}

    for node_label, info in nodes_dict.items():
        external_label = info['external_label']
        properties = info['properties']
        
        # Read the number of node instances from CSV or fall back to default_count
        node_count = counts_map.get(node_label, default_count)

        for i in range(node_count):
            # Generate random field values
            prop_assignments = {}
            for (prop_name, prop_type) in properties:
                if prop_type.upper() == 'STRING':
                    prop_assignments[prop_name] = generate_random_string()
                elif prop_type.upper() == 'INT':
                    prop_assignments[prop_name] = generate_random_int()
                else:
                    prop_assignments[prop_name] = generate_random_string()

            # Node identifier to use when creating relationships, e.g. PostType_0
            node_id = f"{node_label}_{i}"
            node_ids[node_label].append(node_id)

            # Construct the CREATE statement
            prop_list_str = ', '.join(
                f"{k}: {repr(v)}" for k, v in prop_assignments.items()
            )
            statement = f"CREATE ({node_id}:{external_label} {{ {prop_list_str} }});"
            statements.append(statement)

    return statements, node_ids

def generate_cypher_for_relationships(relationships_list, node_ids, counts_map, default_count=4):
    """
    Generates Cypher CREATE statements for relationships.
    - relationships_list: a list (rel_internal_label, start_internal_label, end_internal_label, rel_external_label)
    - node_ids: a dictionary with lists of node identifiers, e.g. node_ids['PostType'] = ["PostType_0", ...]
    - counts_map: a dictionary that may store the number of edges for the key = internal relationship label.
    - default_count: default number of relationships if there is no entry in counts_map.

    Returns a list of Cypher CREATE statements for relationships.
    """
    statements = []
    for (internal_rel_label, start_label, end_label, external_rel_label) in relationships_list:
        # Read the number of relationships from CSV or fall back to default_count
        rel_count = counts_map.get(internal_rel_label, default_count)

        # Skip if there are no start or end nodes available
        if start_label not in node_ids or end_label not in node_ids:
            continue

        possible_starts = node_ids[start_label]
        possible_ends = node_ids[end_label]
        
        for _ in range(rel_count):
            if not possible_starts or not possible_ends:
                continue
            s_node = random.choice(possible_starts)
            e_node = random.choice(possible_ends)
            if s_node != e_node:
                # Create the statement: CREATE (start)-[:REL]->(end)
                statement = f"CREATE ({s_node})-[:{external_rel_label}]->({e_node});"
                statements.append(statement)

    return statements

def read_csv_counts(csv_path):
    """
    Reads a CSV file containing pairs (label, number_of_instances).
    Returns a dictionary counts_map, for example: {"PostType": 12, "PersonType": 10, "KnowsType": 7, ...}
    """
    counts_map = {}
    if not os.path.isfile(csv_path):
        print(f"WARNING: The CSV file '{csv_path}' does not exist. Returning an empty dictionary.")
        return counts_map
    
    with open(csv_path, mode='r', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            if len(row) < 2:
                continue
            label_name = row[0].strip()
            try:
                count_value = int(row[1].strip())
                counts_map[label_name] = count_value
            except ValueError:
                # Skip lines where the second element is not a number
                continue
    return counts_map

def main():
    # Argument parser configuration
    parser = argparse.ArgumentParser(description="PG-Schema to Cypher generator.")
    parser.add_argument("filename", help="File containing the PG-Schema definition.")
    parser.add_argument("-n", "--nodes", type=int, default=None,
                        help="Default number of nodes (for those labels not in the CSV file).")
    parser.add_argument("-e", "--edges", type=int, default=None,
                        help="Default number of relationships (for those labels not in the CSV file).")
    parser.add_argument("-c", "--csv", type=str, default=None,
                        help="CSV file with labels and the number of instances (e.g., PostType,12).")

    args = parser.parse_args()

    # If the user did not provide -n (nodes) or -e (edges), we assume 4 as the default
    default_nodes_count = args.nodes if args.nodes is not None else 4
    default_edges_count = args.edges if args.edges is not None else 4

    # Read the PG-Schema definition file
    with open(args.filename, 'r') as f:
        schema_text = f.read()

    # Parse the schema
    nodes_dict, relationships_list = parse_pg_schema(schema_text)

    # Read the CSV file if provided
    csv_counts_map = {}
    if args.csv:
        csv_counts_map = read_csv_counts(args.csv)

    # Generate nodes
    node_statements, node_ids = generate_cypher_for_nodes(
        nodes_dict,
        counts_map=csv_counts_map,
        default_count=default_nodes_count
    )

    # Generate relationships
    relationship_statements = generate_cypher_for_relationships(
        relationships_list,
        node_ids,
        counts_map=csv_counts_map,
        default_count=default_edges_count
    )

    # Print the results
    print("-- Cypher CREATE statements for nodes --")
    for stmt in node_statements:
        print(stmt)

    print("-- Cypher CREATE statements for relationships --")
    for stmt in relationship_statements:
        print(stmt)

if __name__ == "__main__":
    main()

