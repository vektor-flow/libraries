const pt=72/72.27;
export default {configure(config){config.bibLabelSep=10*pt;},name:'biblatex',kind:'package',dependencies:['url'],options:['style','sorting','backend'],implementedOptions:['style','sorting','backend'],commands:['cite','printbibliography','addbibresource','bibliography','nocite'],
 scope:'Independent BibTeX database parsing, name/year sorting, alphabetic/numeric citation labels and supported entry formatting. Other biblatex styles/filters are diagnosed.'};
