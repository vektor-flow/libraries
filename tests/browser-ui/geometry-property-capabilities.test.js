import {describe,it,expect} from 'vitest';
import {reachablePropertyDescriptors} from 'vektor-flow/property-program';
import {allowedGeometryProperties} from '../../browser-ui/vf-geometry-property-capabilities.mjs';
const descriptors=reachablePropertyDescriptors({geometryKinds:['vertex'],dimension:3,temporal:true});
const names=options=>allowedGeometryProperties(descriptors,options).map(property=>property.name);
describe('native physics property availability',()=>{
  it('keeps geometry and kinematics without offering inactive physics parameters',()=>{
    expect(names({})).toEqual(expect.arrayContaining(['p','v','a','c']));
    for (const property of ['m','q','T']) expect(names({})).not.toContain(property);
  });
  it('offers actual descriptor names from the enabled World modules',()=>{
    const gravity=names({physicsEnabled:true,physics:{gravity:true}});
    expect(gravity).toContain('m');expect(gravity).not.toContain('q');expect(gravity).not.toContain('T');
    const em=names({physicsEnabled:true,physics:{em:true}});
    expect(em).toContain('q');expect(em).not.toContain('T');
  });
});
