// Preset fork publisher for ibm_db; same ci-user / preset-pypi path as the
// other Preset driver forks. Only pull-request builds publish, versioned
// 3.2.3+preset.<n>.pr.<number>.<sha>; artifacts are never overwritten.
podTemplate(
    imagePullSecrets: ['preset-pull'],
    containers: [
        containerTemplate(name: 'ci', image: 'preset/ci:latest',
            ttyEnabled: true, command: 'cat'),
        containerTemplate(name: 'manylinux', image: 'quay.io/pypa/manylinux2014_x86_64:latest',
            ttyEnabled: true, command: 'cat')
    ]
) {
    node(POD_LABEL) {
        checkout scm
        def revision = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
        def baseVersion = readFile('preset/VERSION').trim()
        if (env.CHANGE_ID == null) {
            error('Only pull-request builds publish; use a PR.')
        }
        def version = "${baseVersion}.pr.${env.CHANGE_ID}.${revision.take(12)}"
        def wheel = "ibm_db-${version}-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl"
        def key = "ibm-db/${wheel}"

        container('manylinux') {
            stage('Build and smoke test') {
                withEnv(["PRESET_VERSION=${version}", "OUT=dist"]) {
                    sh '''
                        set -eu
                        rm -rf dist
                        preset/build_wheel.sh
                        /opt/python/cp311-cp311/bin/python -m venv /tmp/smoke
                        /tmp/smoke/bin/pip install --no-deps dist/*.whl
                        /tmp/smoke/bin/python - <<'PY'
import importlib.metadata as im
import os
import ibm_db
import ibm_db_dbi
assert im.version('ibm_db') == os.environ['PRESET_VERSION']
assert ibm_db_dbi.Cursor._fetch_helper
PY
                    '''
                }
            }
        }
        container('ci') {
            stage('Publish immutable wheel') {
                withCredentials([[
                    $class: 'AmazonWebServicesCredentialsBinding',
                    credentialsId: 'ci-user',
                    accessKeyVariable: 'AWS_ACCESS_KEY_ID',
                    secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'
                ]]) {
                    withEnv(["WHEEL=${wheel}", "KEY=${key}",
                             "ALLOW_IDENTICAL_PR_ARTIFACT=true"]) {
                        sh '''
                            set -eu
                            python -m pip install --quiet 'boto3>=1.36,<2'
                            python preset/publish_wheel.py
                        '''
                    }
                }
            }
        }
        archiveArtifacts artifacts: 'dist/*.whl,published.sha256', fingerprint: true
    }
}
