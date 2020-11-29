<template>
  <v-layout column justify-center align-center>
    <v-flex xs12 sm8 md6>
      <div class="text-center"></div>
      <div class="container">
        <div v-if="!signedIn">
          <amplify-authenticator />
        </div>
        <div v-else>
          <amplify-sign-out />
        </div>
      </div>
      <v-card>
        <v-card-title class="headline">
          Christmas Lights Controller
        </v-card-title>
        <v-card-actions>
          <v-spacer />
          <v-btn v-if="signedIn" nuxt color="primary" @click="click_xmas1"
            >XMAS1
          </v-btn>
          <v-btn v-if="signedIn" nuxt color="primary" @click="click_xmas2"
            >XMAS2
          </v-btn>
          <v-btn v-if="signedIn" nuxt color="primary" @click="click_test"
            >TEST
          </v-btn>
          <v-btn v-if="signedIn" nuxt color="primary" @click="click_off"
            >OFF
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-flex>
  </v-layout>
</template>

<script>
import { API, Auth } from 'aws-amplify'
import { AmplifyEventBus } from 'aws-amplify-vue'

export default {
  data() {
    return {
      signedIn: false,
    }
  },
  created() {
    this.findUser()

    AmplifyEventBus.$on('authState', (info) => {
      if (info === 'signedIn') {
        this.findUser()
      } else {
        this.signedIn = false
      }
    })
  },
  methods: {
    async findUser() {
      try {
        const user = await Auth.currentAuthenticatedUser()
        this.signedIn = true
        console.log(user) // eslint-disable-line no-console
      } catch (err) {
        this.signedIn = false
      }
    },
    click_off() {
      console.log('off clicked') // eslint-disable-line no-console
      const payload = {
        body: {},
        headers: {},
        queryStringParameters: {
          thing_name: 'ThomasLights2',
        },
      }
      API.post('ws281xapi', '/off', payload).catch((error) => {
        console.log(error.response) // eslint-disable-line no-console
      })
    },
    click_test() {
      console.log('test clicked') // eslint-disable-line no-console
      const payload = {
        body: {},
        headers: {},
        queryStringParameters: {
          thing_name: 'ThomasLights2',
        },
      }
      API.post('ws281xapi', '/effect/TestPattern', payload).catch((error) => {
        console.log(error.response) // eslint-disable-line no-console
      })
    },
    click_xmas1() {
      console.log('test clicked') // eslint-disable-line no-console
      const payload = {
        body: {},
        headers: {},
        queryStringParameters: {
          thing_name: 'ThomasLights2',
        },
      }
      API.post('ws281xapi', '/effect/Christmas1', payload).catch((error) => {
        console.log(error.response) // eslint-disable-line no-console
      })
    },
    click_xmas2() {
      console.log('test clicked') // eslint-disable-line no-console
      const payload = {
        body: {},
        headers: {},
        queryStringParameters: {
          thing_name: 'ThomasLights2',
        },
      }
      API.post('ws281xapi', '/effect/Christmas2', payload).catch((error) => {
        console.log(error.response) // eslint-disable-line no-console
      })
    },
  },
}
</script>
