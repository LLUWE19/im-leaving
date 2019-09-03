#!/usr/bin/env python2
# -*-: coding utf-8 -*-

from hermes_python.hermes import Hermes
import requests as rq
import ConfigParser
import json
import io

CONFIGURATION_ENCODING_FORMAT = "utf-8"
CONFIGURATION_INI = "config.ini"

MQTT_IP_ADDR = "192.168.0.136"
MQTT_PORT = 1883
MQTT_ADDR = "{}:{}".format(MQTT_IP_ADDR, str(MQTT_PORT))

INTENT_LEAVING = "LLUWE19:user_leaving_home"
INTENT_ANSWER = "LLUWE19:user_gives_answer"
INTENT_PERCENTAGE = "LLUWE19:user_gives_percentage"
INTENT_COLOR = "LLUWE19:user_gives_color"

last_question = None
light_on = False
light_color = None
light_brightness = None
tv_on = False
SessionStates = {}


class SnipsConfigParser(ConfigParser.SafeConfigParser):
    def to_dict(self):
        return {section: {option_name : option for option_name, option in self.items(section)} for section in self.sections()}


def read_configuration_file(configuration_file):
    try:
        with io.open(configuration_file, encoding=CONFIGURATION_ENCODING_FORMAT) as f:
            conf_parser = SnipsConfigParser()
            conf_parser.readfp(f)
            return conf_parser.to_dict()
    except (IOError, ConfigParser.Error) as e:
        return dict()


def user_leaving_home(hermes, intent_message):
    global last_question
    sentence = "okay. should i turn the lights off"
    last_question = sentence
    hermes.publish_continue_session(intent_message.session_id, sentence, [INTENT_ANSWER])


def user_gives_answer(hermes, intent_message):
    global light_brightness
    global light_color
    global light_on
    global tv_on
    global last_question

    print("light_brightness: ", light_brightness)
    print("light_color ", light_color)
    print("light_on: ", light_on)
    print("tv_on ", tv_on)
    print("Last_question: ", last_question)

    conf = read_configuration_file(CONFIGURATION_INI)
    autho = conf['secret']['http_api_password']
    header = {
        'Authorization': autho,
        "Content-Type": "application/json",
    }
    session_id = intent_message.session_id

    answer = None

    if intent_message.slots.answer:
        answer = intent_message.slots.answer.first().value
        print("The user answered: " + answer)

    if intent_message.slots.color:
        print("message with color")
        light_color = intent_message.slots.color.first().value

    if intent_message.slots.percentage:
        print("message with brightness")
        light_brightness = intent_message.slots.percentage.first().value

    if last_question == "okay. should i turn the lights off":
        if answer == "yes":
            light_on = False
            sentence = "okay... should i turn the tee vee off"
            last_question = sentence
            hermes.publish_continue_session(session_id, sentence, [INTENT_ANSWER])
        else:
            light_on = True
            sentence = "okay... did you want to change the light color"
            last_question = sentence
            hermes.publish_continue_session(session_id, sentence, [INTENT_COLOR])

    elif last_question == "okay... did you want to change the light color":
        sentence = "okay... how bright do you want the light"
        last_question = sentence
        hermes.publish_continue_session(session_id, sentence, [INTENT_PERCENTAGE])

    elif last_question == "okay... how bright do you want the light":
        sentence = "okay... should i turn the tee vee off"
        last_question = sentence
        hermes.publish_continue_session(session_id, sentence, [INTENT_ANSWER])

    elif last_question == "okay... should i turn the tee vee off":
        if answer == "yes":
            tv_on = False
        else:
            tv_on = True
        sentence = "okay... goodbye"

        if not light_on:
            print("Turning the lights off")
            url = 'http://192.168.0.136:8123/api/services/light/turn_off'
            body = {
                "entity_id": "light.tall_lamp"
            }
            json_body = json.dumps(body)
            print(json_body)
            request = rq.post(url, data=json_body, headers=header)
        else:
            url = 'http://192.168.0.136:8123/api/services/light/turn_on'
            body = {
                "entity_id": "light.tall_lamp",
                "color_name": light_color,
                "brightness_pct": light_brightness
            }
            json_body = json.dumps(body)
            print(json_body)
            request = rq.post(url, data=json_body, headers=header)

        if tv_on:
            print("Leaving the tv on")
        else:
            url = 'http://192.168.0.136:8123/api/services/switch/turn_off'
            body = {
                "entity_id": "switch.living_room_tv"
            }
            json_body = json.dumps(body)
            request = rq.post(url, data=json_body, headers=header)

        last_question = sentence
        hermes.publish_end_session(session_id, sentence)


with Hermes(MQTT_ADDR) as h:

    h.subscribe_intent(INTENT_LEAVING, user_leaving_home) \
        .subscribe_intent(INTENT_ANSWER, user_gives_answer) \
        .subscribe_intent(INTENT_COLOR, user_gives_answer) \
        .subscribe_intent(INTENT_PERCENTAGE, user_gives_answer) \
        .start()









