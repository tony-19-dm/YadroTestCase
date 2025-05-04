import xml.etree.ElementTree as ET
import json
from collections import defaultdict, OrderedDict

def parse_xml_model(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    classes = OrderedDict()
    aggregations = []
    
    class_order = [
        "MetricJob", "CPLANE", "MGMT", "RU", "HWE", "COMM", "BTS"
    ]
    
    for class_name in class_order:
        classes[class_name] = None
    
    for elem in root.findall('Class'):
        class_name = elem.get('name')
        is_root = elem.get('isRoot', 'false').lower() == 'true'
        documentation = elem.get('documentation', '')
        
        attributes = []
        for attr in elem.findall('Attribute'):
            attributes.append(OrderedDict([
                ('name', attr.get('name')),
                ('type', attr.get('type'))
            ]))
        
        classes[class_name] = OrderedDict([
            ('name', class_name),
            ('isRoot', is_root),
            ('documentation', documentation),
            ('attributes', attributes)
        ])
    
    for elem in root.findall('Aggregation'):
        source = elem.get('source')
        target = elem.get('target')
        source_multiplicity = elem.get('sourceMultiplicity')
        target_multiplicity = elem.get('targetMultiplicity')
        
        if '..' in source_multiplicity:
            source_min, source_max = source_multiplicity.split('..')
        else:
            source_min = source_max = source_multiplicity
            
        aggregations.append(OrderedDict([
            ('source', source),
            ('target', target),
            ('source_min', source_min),
            ('source_max', source_max),
            ('target_min', target_multiplicity),
            ('target_max', target_multiplicity)
        ]))
    
    return classes, aggregations

def generate_meta_json(classes, aggregations):
    source_info = defaultdict(dict)
    for agg in aggregations:
        source_info[agg['source']][agg['target']] = {
            'max': agg['source_max'],
            'min': agg['source_min']
        }
    
    meta_data = []
    
    for class_name in classes:
        cls = classes[class_name]
        if cls is None:
            continue

        min_val = None
        max_val = None
        
        if class_name in source_info:

            target = next(iter(source_info[class_name]))
            max_val = source_info[class_name][target]['max']
            min_val = source_info[class_name][target]['min']
        
        parameters = []
        
        for attr in cls['attributes']:
            parameters.append(OrderedDict([
                ('name', attr['name']),
                ('type', attr['type'])
            ]))
        
        contained_classes = []
        for agg in aggregations:
            if agg['target'] == class_name:
                contained_classes.append(OrderedDict([
                    ('name', agg['source']),
                    ('type', 'class')
                ]))
        
        if class_name == 'MGMT':
            contained_classes.sort(key=lambda x: 0 if x['name'] == 'MetricJob' else 1)
        
        parameters.extend(contained_classes)
        
        meta_entry = OrderedDict([
            ('class', class_name),
            ('documentation', cls['documentation']),
            ('isRoot', cls['isRoot']),
        ])
        
        if max_val is not None and min_val is not None:
            meta_entry['max'] = max_val
            meta_entry['min'] = min_val
        
        meta_entry['parameters'] = parameters
        meta_data.append(meta_entry)
    
    return json.dumps(meta_data, indent=4)

def build_class_hierarchy(aggregations):
    """Build the class hierarchy based on aggregations"""
    root_class = 'BTS'

    containment = defaultdict(list)
    for agg in aggregations:
        containment[agg['target']].append({
            'class': agg['source'],
            'max': agg['source_max'],
            'min': agg['source_min']
        })
    
    return root_class, containment

def generate_config_xml(classes, root_class, containment):
    """Generate the config.xml file structure"""
    def build_element(class_name, indent=0):
        cls = classes[class_name]
        indent_str = '    ' * indent
        element_lines = [f"{indent_str}<{class_name}>"]
        
        for attr in cls['attributes']:
            element_lines.append(f"{indent_str}    <{attr['name']}>{attr['type']}</{attr['name']}>")
        
        if class_name in containment:
            contained = containment[class_name]
            if class_name == 'MGMT':
                contained.sort(key=lambda x: 0 if x['class'] == 'MetricJob' else 1)
            elif class_name == 'BTS':
                contained.sort(key=lambda x: ['MGMT', 'HWE', 'COMM'].index(x['class']))
            
            for item in contained:
                element_lines.extend(build_element(item['class'], indent + 1))
        
        element_lines.append(f"{indent_str}</{class_name}>")
        return element_lines
    
    lines = build_element(root_class)
    return '\n'.join(lines)

def main():
    input_file = 'input/test_input.xml'
    config_output = 'out/config.xml'
    meta_output = 'out/meta.json'
    
    classes, aggregations = parse_xml_model(input_file)
    
    root_class, containment = build_class_hierarchy(aggregations)
    
    config_xml = generate_config_xml(classes, root_class, containment)
    with open(config_output, 'w') as f:
        f.write(config_xml)
    
    meta_json = generate_meta_json(classes, aggregations)
    with open(meta_output, 'w') as f:
        f.write(meta_json)
    
    print(f"Successfully generated {config_output} and {meta_output}")

if __name__ == '__main__':
    main()