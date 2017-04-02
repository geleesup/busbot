import os
from slackclient import SlackClient
import time

DO_COMMAND = 'do'

READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose


class BotClient:
    
    def __init__(self, botName, botTokenEnvVar, callback=None):
        self._botName = botName
        self._isConnected = False
        self.slack_client = SlackClient(os.environ.get(botTokenEnvVar))
        self._botID = self.getBotID()
        self._callback = callback

        self.AT_BOT = '<@' + self._botID + '>'

    def testCallback(self):
        return self._callback()

    def getBotID(self):
        api_call = self.slack_client.api_call('users.list')

        botID = ''

        if api_call.get('ok'):
            # retrieve all users so we can find our bot
            users = api_call.get('members')
            for user in users:
                if 'name' in user and user.get('name') == self._botName:
                    botID = user.get('id')
        else:
            print("could not find bot user with the name " + self._botName)

        return botID

    def connect(self):
        if self.slack_client.rtm_connect():
            print '%s connected and running!' % self._botName
            self._isConnected = True

        else:
            print("Connection failed. Invalid Slack token or bot ID?")
            self._isConnected = False

        return self._isConnected


    def read(self):
        if not self._isConnected:
            return

        command, channel = self.parse_slack_output(self.slack_client.rtm_read())

        if command and channel:
            self.handle_command(command, channel)

    def runServer(self):
        if not self._isConnected:
            return

        while True:
            command, channel = self.parse_slack_output(self.slack_client.rtm_read())
            if command and channel:
                self.handle_command(command, channel)
            time.sleep(READ_WEBSOCKET_DELAY)


    def handle_command(self, command, channel):
        """
            Receives commands directed at the bot and determines if they
            are valid commands. If so, then acts on the commands. If not,
            returns back what it needs for clarification.
        """
        response = "Not sure what you mean. Use the *" + DO_COMMAND + \
                   "* command with numbers, delimited by spaces."
        if command.startswith(DO_COMMAND):
            if self._callback is None:
                response = "Sure...write some more code then I can do that!"
            else:
                response = self.testCallback()

        self.slack_client.api_call("chat.postMessage", channel=channel,
                              text=response, as_user=True)
    
    
    def parse_slack_output(self, slack_rtm_output):
        """
            The Slack Real Time Messaging API is an events firehose.
            this parsing function returns None unless a message is
            directed at the Bot, based on its ID.
        """
        output_list = slack_rtm_output
        if output_list and len(output_list) > 0:
            for output in output_list:
                if output and 'text' in output and self.AT_BOT in output['text']:
                    # return text after the @ mention, whitespace removed
                    return output['text'].split(self.AT_BOT)[1].strip().lower(), \
                           output['channel']
        return None, None
        
