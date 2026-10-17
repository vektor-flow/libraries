"""Python3.14 serializes generic installed registry metadata, never a document."""
import json,subprocess,sys
from pathlib import Path
assert sys.version_info[:2]==(3,14)
root=Path(__file__).resolve().parent
script="""import{pathToFileURL}from'node:url';const root=process.argv[1];const{supportedModules}=await import(pathToFileURL(root+'/latex-modules/registry.mjs')),data={};for(const name of supportedModules.packages){const{default:module}=await import(pathToFileURL(root+'/latex-modules/packages/'+(name==='color'?'xcolor':name)+'.mjs'));data[name]={dependencies:module.dependencies??[],options:module.options??[],implementedOptions:module.implementedOptions??[]};}const classes={};for(const name of supportedModules.classes){const{default:module}=await import(pathToFileURL(root+'/latex-modules/classes/'+name+'.mjs'));classes[name]=module.dependencies??[];}process.stdout.write(JSON.stringify({packages:data,classes}));"""
raw=subprocess.run(['node','--input-type=module','-e',script,str(root.parent)],text=True,capture_output=True,check=True).stdout
data=json.loads(raw)
(root/'document_module_data.vkf').write_text('# Generic installed package registry metadata. Runtime decisions remain VKF.\nsource()->str:'+json.dumps(json.dumps(data['packages'],ensure_ascii=False,separators=(',',':')),ensure_ascii=False)+'\nclasses()->str:'+json.dumps(json.dumps(data['classes'],ensure_ascii=False,separators=(',',':')),ensure_ascii=False)+'\n')
