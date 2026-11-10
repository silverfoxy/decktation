// workflow_run's GITHUB_SHA identifies master, not the generated Pages snapshot.
// Deploy with the checked-out gh-pages commit so distinct artifacts get distinct IDs.
async function deployPages({ github, core, context, snapshot, artifactId, wait = ms => new Promise(resolve => setTimeout(resolve, ms)), polls = 120 }) {
  if (!/^[0-9a-f]{40}$/.test(snapshot)) throw new Error('Invalid Pages snapshot commit');
  const repo = context.repo;
  // Use this upload's output: reruns can leave multiple artifacts with the same name.
  if (!/^[1-9][0-9]*$/.test(String(artifactId))) throw new Error('Invalid Pages artifact ID');
  const { data: deployment } = await github.request('POST /repos/{owner}/{repo}/pages/deployments', {
    ...repo, artifact_id: artifactId, pages_build_version: snapshot, oidc_token: await core.getIDToken(),
  });
  let errors = 0;
  for (let attempt = 0; attempt < polls; attempt++) {
    await wait(5000);
    let status;
    try {
      ({ data: status } = await github.request('GET /repos/{owner}/{repo}/pages/deployments/{deploymentId}', {
        ...repo, deploymentId: deployment.id,
      }));
      errors = 0;
    } catch (error) {
      if (error.status < 500 || ++errors >= 10) throw error;
      continue;
    }
    if (status.status === 'succeed') {
      core.setOutput('page_url', deployment.page_url);
      return deployment;
    }
    if (/failed|cancelled|lost/.test(status.status)) throw new Error(`Pages deployment ${status.status}`);
  }
  await github.request('POST /repos/{owner}/{repo}/pages/deployments/{deploymentId}/cancel', {
    ...repo, deploymentId: deployment.id,
  });
  throw new Error('Pages deployment timed out');
}

module.exports = { deployPages };
