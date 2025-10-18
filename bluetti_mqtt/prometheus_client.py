import logging
from typing import List
from bluetti_mqtt.bus import EventBus, ParserMessage
from bluetti_mqtt.core import BluettiDevice
from bluetti_mqtt.mqtt_client import NORMAL_DEVICE_FIELDS, MqttFieldType
from prometheus_client import start_http_server, Gauge, Info

PROMETHEUS_FIELDS = {
    'dc_input_power': Gauge('bluetti_dc_input_power','DC input power'),
    'ac_input_power': Gauge('bluetti_ac_input_power','AC input power'),
    'ac_output_power': Gauge('bluetti_ac_output_power','AC output power'),
    'dc_output_power': Gauge('bluetti_dc_output_power','DC output power'),
    'power_generation': Gauge('bluetti_power_generation','Power generation'),
    'total_battery_percent': Gauge('bluetti_total_battery_percent','Total battery percent'),
    'ac_output_on': Gauge('bluetti_ac_output_on','AC output on'),
    'dc_output_on': Gauge('bluetti_dc_output_on','DC output on'),
    'ac_output_mode': Gauge('bluetti_ac_output_mode','AC aoutput mode'),
    'internal_ac_voltage': Gauge('bluetti_internal_ac_voltage','Internal AC voltage'),
    'internal_current_one': Gauge('bluetti_internal_current_one','Internal current one'),
    'internal_power_one': Gauge('bluetti_internal_power_one','Internal power one'),
    'internal_ac_frequency': Gauge('bluetti_internal_ac_frequency','Internal AC frequency'),
    'internal_current_two': Gauge('bluetti_internal_current_two','Internal current two'),
    'internal_power_two': Gauge('bluetti_internal_power_two','Internal power two'),
    'ac_input_voltage': Gauge('bluetti_ac_input_voltage','AC input voltage'),
    'internal_current_three': Gauge('bluetti_internal_current_three','Internal current three'),
    'internal_power_three': Gauge('bluetti_internal_power_three','Internal power three'),
    'ac_input_frequency': Gauge('bluetti_ac_input_frequency','AC input frequency'),
    'total_battery_voltage': Gauge('bluetti_total_battery_voltage','Total battery voltage'),
    'total_battery_current': Gauge('bluetti_total_battery_current','Total battery current'),
    'ups_mode': Gauge('bluetti_ups_mode','UPS mode'),
    'split_phase_on': Gauge('bluetti_split_phase_on','Split phase on'),
    'split_phase_machine_mode': Gauge('bluetti_split_phase_machine_mode','Split phase machine mode'),
    'grid_charge_on': Gauge('bluetti_grid_charge_on','Grid charge on'),
    'time_control_on': Gauge('bluetti_time_control_on','Time control on'),
    'battery_range_start': Gauge('bluetti_battery_range_start','Battery range start'),
    'battery_range_end': Gauge('bluetti_battery_range_end','Battery range end'),
    'max_grid_charge_current': Gauge('bluetti_max_grid_charge_current','Max grid charge current'),
    'led_mode': Gauge('bluetti_led_mode','LED mode'),
    'power_off': Gauge('bluetti_power_off','Power off'),
    'auto_sleep_mode': Gauge('bluetti_auto_sleep_mode','Auto sleep mode'),
    'eco_on': Gauge('bluetti_eco_on','Eco on'),
    'eco_shutdown': Gauge('bluetti_eco_shutdown','Eco shutdown'),
    'charging_mode': Gauge('bluetti_charging_mode','Charging mode'),
    'power_lifting_on': Gauge('bluetti_power_lifting_on','Power lifting on'),
    'dc_input_voltage1': Gauge('bluetti_dc_input_voltage1','DC input voltage1'),
    'dc_input_power1': Gauge('bluetti_dc_input_power1','DC input power1'),
    'dc_input_current1': Gauge('bluetti_dc_input_current1','DC input current1'),
    'pack_voltage': Gauge('bluetti_pack_voltage','Pack voltage',['pack_num']),
    'pack_battery_percent': Gauge('bluetti_pack_battery_percent','Pack battery percent',['pack_num']),
    'internal_dc_input_voltage': Gauge('bluetti_internal_dc_input_voltage','Internal DC input voltage'),
    'internal_dc_input_current': Gauge('bluetti_internal_dc_input_current','Internal DC input current'),
    'internal_dc_input_power': Gauge('bluetti_internal_dc_input_power','Internal DC input power')
}

class PrometheusClient:
    def __init__(
        self,
        bus: EventBus,
        port: int = 9219,
    ):
        self.bus = bus
        self.port = port
        self.device_info = Info('device_info', 'Info about the device')

    def start(self):
        logging.info(f"Starting Prometheus client on port {self.port}...")
        self.bus.add_parser_listener(self.handle_message)
        start_http_server(self.port)

    async def handle_message(self, msg: ParserMessage):
        logging.debug(f'Got a message from {msg.device}: {msg.parsed}')

        # Publish device info
        self.device_info.info({'device': msg.device.type, 'sn': msg.device.sn})

        # Publish normal fields
        for name, value in msg.parsed.items():
            # Skip unconfigured fields
            if name not in PROMETHEUS_FIELDS:
                continue

            # Build payload string
            field = NORMAL_DEVICE_FIELDS[name]
            if field.type == MqttFieldType.NUMERIC:
                payload = str(value)
            elif field.type == MqttFieldType.BOOL or field.type == MqttFieldType.BUTTON:
                payload = 'ON' if value else 'OFF'
            elif field.type == MqttFieldType.ENUM:
                payload = value.name
            else:
                assert False, f'Unhandled field type: {field.type.name}'

            # Publish prometheus field
            if (field.type in [MqttFieldType.NUMERIC]):
                PROMETHEUS_FIELDS[name].set(payload)

        # Publish battery pack data
        pack_details = self._build_pack_details(msg.parsed)
        if 'pack_num' in msg.parsed and len(pack_details) > 0:
            if ('percent' in pack_details.keys()): PROMETHEUS_FIELDS['pack_battery_percent'].labels(msg.parsed["pack_num"]).set(pack_details['percent'])
            if ('voltage' in pack_details.keys()): PROMETHEUS_FIELDS['pack_voltage'].labels(msg.parsed["pack_num"]).set(pack_details['voltage'])

        # Publish DC input data
        if 'internal_dc_input_voltage' in msg.parsed:
            PROMETHEUS_FIELDS['internal_dc_input_voltage'].set(payload)
        if 'internal_dc_input_power' in msg.parsed:
            PROMETHEUS_FIELDS['internal_dc_input_power'].set(payload)
        if 'internal_dc_input_current' in msg.parsed:
            PROMETHEUS_FIELDS['internal_dc_input_current'].set(payload)

    def _build_pack_details(self, parsed: dict):
        details = {}
        if 'pack_status' in parsed:
            details['status'] = parsed['pack_status'].name
        if 'pack_battery_percent' in parsed:
            details['percent'] = parsed['pack_battery_percent']
        if 'pack_voltage' in parsed:
            details['voltage'] = float(parsed['pack_voltage'])
        if 'cell_voltages' in parsed:
            details['voltages'] = [float(d) for d in parsed['cell_voltages']]
        return details