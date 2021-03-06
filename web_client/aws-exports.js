/* eslint-disable */
// WARNING: DO NOT EDIT. This file is automatically generated by AWS Amplify. It will be overwritten.

const awsmobile = {
  aws_project_region: 'eu-west-1',
  aws_cognito_identity_pool_id:
    'eu-west-1:009466f0-5099-4590-9ee1-7c172c14b1ff',
  aws_cognito_region: 'eu-west-1',
  aws_user_pools_id: 'eu-west-1_gjkbuYvcP',
  aws_user_pools_web_client_id: '2su34kutm86q0m7vcgfjks1at0', // TODO remove these id values to parameter store
  oauth: {
    domain: 'idp.debsanddarren.com',
    scope: [
      'phone',
      'email',
      'openid',
      'profile',
      'aws.cognito.signin.user.admin',
    ],
    redirectSignIn: 'https://www.google.co.uk/',
    redirectSignOut: 'https://www.google.co.uk/',
    responseType: 'code',
  },
  federationTarget: 'COGNITO_USER_POOLS',
  aws_cloud_logic_custom: [
    {
      name: 'ws281xapi',
      //endpoint: 'https://tmtiqr7byh.execute-api.eu-west-1.amazonaws.com/prod',
      endpoint: 'https://api.debsanddarren.com/ledstrip',
      region: 'eu-west-1',
    },
  ],
}

export default awsmobile
