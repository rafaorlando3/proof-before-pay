"""Check the installation contracts that failed in the licensed native IPM trial."""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(__file__).resolve().parents[2]
export = ET.parse(root / 'module.xml').getroot()
document = export.find('Document')
module = document.find('Module')
assert document.attrib['name'] == module.findtext('Name') + '.ZPM'
assert re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', module.findtext('Version'))
assert module.findtext('Packaging') == 'module'
assert module.findtext('SourcesRoot') == 'cls'

classes = {
    '.'.join(path.relative_to(root / 'cls').with_suffix('').parts) + '.CLS'
    for path in (root / 'cls').rglob('*.cls')
    if path.relative_to(root / 'cls').parts[:2] != ('pbp', 'Test')
}
assert {resource.attrib['Name'] for resource in module.findall('Resource')} == classes
assert all(name.endswith('.CLS') for name in classes), 'no application data globals'

packages = {'pbp_guard', 'pbp_ledger', 'pbp_refund_target', 'pbp_review', 'pbp_s0_core', 'pbp_witness'}
expected = {'python/' + name + '/': '${mgrdir}python/' + name + '/' for name in packages}
expected.update({name + '/': '${mgrdir}proof-before-pay/' + name + '/' for name in ('ui', 'policy', 'fixtures')})
copies = module.findall('FileCopy')
assert {copy.attrib['Name']: copy.attrib['Target'] for copy in copies} == expected
for copy in copies:
    assert copy.attrib['Overlay'] in ('0', '1'), 'IPM FileCopy uses numeric Boolean values'
    assert copy.attrib['Overlay'] == '0'
    assert (root / copy.attrib['Name']).is_dir()

invoke = module.find('Invoke')
assert invoke.attrib == {'Class': 'pbp.Setup', 'Method': 'Install', 'Phase': 'Configure', 'When': 'After', 'CheckStatus': '1'}
assert [arg.text for arg in invoke.findall('Arg')] == ['${mgrdir}proof-before-pay', '0']
assert (root / 'requirements.txt').read_bytes() == (root / 'requirements.lock').read_bytes()
print(json.dumps({'ok': True, 'application_classes': len(classes), 'native_python_packages': len(packages),
                  'numeric_Boolean_and_package_scoped_targets': True, 'automatic_production_start': False,
                  'native_IPM_runtime_test_replaced': False}))
