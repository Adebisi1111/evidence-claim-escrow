const { createClient, chains } = require('genlayer-js');
const { privateKeyToAccount } = require('viem/accounts');

const CONTRACT = '0x6AFd84eA38FfFADB06B92E4924c2474056B9f6b9';
const MAIN_KEY = '0x023d076ab40ea46c59ac7ca7cecfaa2db5fa10b7a481aef27cf68e9cc5a8c0af';

async function main() {
  const account = privateKeyToAccount(MAIN_KEY);
  const client = createClient({ chain: chains.testnetBradbury, account });
  
  console.log('Address:', account.address);
  
  const balanceBefore = await client.getBalance({ address: account.address });
  console.log('Balance before:', balanceBefore.toString(), 'wei =', Number(balanceBefore) / 1e18, 'GEN');
  
  // Submit claim with reachable evidence URL
  console.log('\n--- Submit Claim ---');
  const evidenceUrl = 'https://httpbin.org/get';
  const tx = await client.writeContract({
    address: CONTRACT,
    functionName: 'submit_claim',
    args: ['claim-test-1', 'The Earth orbits the Sun', evidenceUrl, 'Science', account.address],
    value: 100000000000000000n, // 0.1 GEN
  });
  console.log('Tx hash:', tx);
  
  // Wait
  console.log('\nWaiting 30 seconds...');
  await new Promise(r => setTimeout(r, 30000));
  
  // Check claim
  const claim = await client.readContract({
    address: CONTRACT,
    functionName: 'get_claim',
    args: ['claim-test-1'],
  });
  console.log('Claim:', claim);
  
  // Resolve claim
  console.log('\n--- Resolve Claim ---');
  const tx2 = await client.writeContract({
    address: CONTRACT,
    functionName: 'resolve_claim',
    args: ['claim-test-1'],
  });
  console.log('Tx hash:', tx2);
  
  // Wait
  console.log('\nWaiting 30 seconds...');
  await new Promise(r => setTimeout(r, 30000));
  
  // Check claim after resolution
  const claimAfter = await client.readContract({
    address: CONTRACT,
    functionName: 'get_claim',
    args: ['claim-test-1'],
  });
  console.log('Claim after resolve:', claimAfter);
  
  const balanceAfter = await client.getBalance({ address: account.address });
  console.log('\nBalance after:', balanceAfter.toString(), 'wei =', Number(balanceAfter) / 1e18, 'GEN');
  console.log('Delta:', (balanceAfter - balanceBefore).toString(), 'wei');
  
  console.log('\n=== Test Complete ===');
}

main().catch(console.error);
