// Convert the canonical VKF tagged numeric-array ABI entirely on the GPU.
// The output buffer is shared with the existing16-float vertex instance ABI.
struct Parameters { rows:u32, count:u32, segments:u32, padding:u32 }
@group(0) @binding(0) var<storage,read> source:array<u32>;
@group(0) @binding(1) var<storage,read_write> instances:array<u32>;
@group(0) @binding(2) var<uniform> params:Parameters;
@group(0) @binding(3) var<storage,read_write> errors:atomic<u32>;
@group(0) @binding(4) var<storage,read> mapping:array<vec4<u32>>;
fn word(address:u32)->u32 {
    if((address&3u)!=0u){atomicOr(&errors,1u);return 0u;}
    var low=0u;var high=params.segments;
    while(low<high){
        let middle=(low+high)/2u;let entry=mapping[middle];
        if(address<entry.x){high=middle;}
        else if(address>=entry.y){low=middle+1u;}
        else{return source[entry.z+(address-entry.x)/4u];}
    }
    atomicOr(&errors,1u);return 0u;
}
fn rounded(hi:u32,lo:u32,shift:u32)->u32 {
    var kept:u32; var greater=false; var equal=false;
    if(shift<32u){
        kept=(hi<<(32u-shift))|(lo>>shift);
        let lost=lo&((1u<<shift)-1u);let half=1u<<(shift-1u);
        greater=lost>half;equal=lost==half;
    }else if(shift==32u){kept=hi;greater=lo>0x80000000u;equal=lo==0x80000000u;}
    else{
        let n=shift-32u;kept=hi>>n;
        let lost=hi&((1u<<n)-1u);let half=1u<<(n-1u);
        greater=lost>half || (lost==half && lo!=0u);equal=lost==half && lo==0u;
    }
    if(greater || (equal && (kept&1u)!=0u)){kept+=1u;}
    return kept;
}
fn float32bits(lo:u32,hi:u32)->u32 {
    let sign=hi&0x80000000u;let exponent=(hi>>20u)&2047u;
    if(exponent==0u){return sign;}
    if(exponent==2047u){atomicOr(&errors,2u);return sign;}
    let e=i32(exponent)-1023;
    if(e < -150){return sign;}
    if(e > 127){return sign|0x7f800000u;}
    let mantissa=(hi&0xfffffu)|0x100000u;
    if(e < -126){return sign|rounded(mantissa,lo,u32(-e-97));}
    return sign|((u32(e+126)<<23u)+rounded(mantissa,lo,29u));
}
@compute @workgroup_size(64)
fn pack(@builtin(global_invocation_id) invocation:vec3<u32>){
    let i=invocation.x;if(i>=params.count*16u){return;}
    if(word(params.rows)!=4u || word(params.rows+4u)!=params.count){atomicOr(&errors,4u);return;}
    let row=word(word(params.rows+8u)+(i/16u)*4u);
    if(word(row)!=4u || word(row+4u)!=16u){atomicOr(&errors,8u);return;}
    let number=word(word(row+8u)+(i%16u)*4u);
    if(word(number)!=2u){atomicOr(&errors,16u);return;}
    instances[i]=float32bits(word(number+8u),word(number+12u));
}
