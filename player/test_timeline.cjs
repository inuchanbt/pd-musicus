const assert=require('node:assert/strict');
const {validate,stateAt,indexAt}=require('./timeline.js');
const score={schema_version:1,timebase:'arranged_audio_seconds',duration_s:10,timeline:[
 {at_s:1,label:'Request',data:{actual_power_W:120}},
 {at_s:2,label:'Accept'},
 {at_s:3,label:'Hard Reset',kind:'hard_reset'},
 {at_s:4,label:'Request',data:{actual_power_W:24}},
 {at_s:4,label:'Accept'}]};
validate(score);
assert.equal(stateAt(score,0).event,null);
assert.equal(stateAt(score,2.5).power,120);
assert.equal(stateAt(score,3).power,null);
assert.equal(stateAt(score,4).index,4);
assert.equal(stateAt(score,1.1).power,120); // backward seek restores earlier data
assert.equal(indexAt([],1),-1);
assert.equal(indexAt([{at_s:2.008928571}],2.008928),0); // browser seek rounding
assert.equal(stateAt(score,10).power,24);
assert.throws(()=>validate({...score,schema_version:2}));
assert.throws(()=>validate({...score,timeline:[{at_s:NaN,label:'bad'}]}));
assert.throws(()=>validate({...score,timeline:[{at_s:2,label:'a'},{at_s:1,label:'b'}]}));
assert.throws(()=>validate({...score,timeline:[{at_s:1,label:'bad',data:{statuses:'failed'}}]}));
assert.throws(()=>validate({...score,timeline:[{at_s:1,label:'bad',data:{actual_power_W:-1}}]}));
console.log('Timeline tests passed: seeks, resets, simultaneous events, validation.');
