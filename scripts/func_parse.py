#! /usr/bin/env python


"""
Header
bytes, type/description
4, unsigned integer magic number 0xadbccbda
4, unsigned integer schema number
4, integer type of message, 0 for heartbeat, 1 for status, 2 for decode


"""

import socket
import inspect
import datetime
import pandas as pd

# import time
import struct
from typing import Any


def get_int8(data, index):
    value = struct.unpack(">b", data[index : index + 1])[0]
    return value, index + 1


def get_int32(data, index):
    value = struct.unpack(">i", data[index : index + 4])[0]
    return value, index + 4


def get_int64(data, index):
    value = struct.unpack(">q", data[index : index + 8])[0]
    return value, index + 8


def get_unsigned32(data, index):
    value = struct.unpack(">I", data[index : index + 4])[0]
    return value, index + 4


def get_utf8(data, index):
    length = struct.unpack(">i", data[index : index + 4])[0]
    if length <= 0:
        length = 0
        message = ""
    else:
        message = data[index + 4 : index + 4 + length].decode("utf-8")
    new_index = index + 4 + length
    return message, new_index


def get_bool(data, index):
    value = struct.unpack(">?", data[index : index + 1])[0]
    return value, index + 1


def get_time(data, index):
    milliseconds_since_midnight, index = get_unsigned32(data, index)
    seconds_since_midnight = milliseconds_since_midnight / 1000.0
    utc_time = datetime.datetime.utcnow()
    utc_date = datetime.datetime(utc_time.year, utc_time.month, utc_time.day)
    time = utc_date + datetime.timedelta(seconds=seconds_since_midnight)
    return time, index


def get_double(data, index):
    value = struct.unpack(">d", data[index : index + 8])[0]
    return value, index + 8


def get_datetime_tuple(data, index):
    date_val, index = get_int64(data, index)
    time_val, index = get_time(data, index)
    timespec, index = get_int8(data, index)
    return (date_val, time_val, timespec), index


def time_tuple_to_timestamp(time_tuple):
    date_val, time_val, timespec = time_tuple
    timestamp = pd.to_datetime(date_val, unit="D", origin="julian") + pd.to_timedelta(
        time_val, unit="s"
    )
    return timestamp


def _decode_heartbeat(rec, data, index):
    rec["packet_id"], index = get_utf8(data, index)
    rec["max_schema_number"], index = get_int32(data, index)
    rec["version"], index = get_utf8(data, index)
    rec["revision"], index = get_utf8(data, index)
    return rec, index


def _decode_status(rec, data, index):
    rec["packet_id"], index = get_utf8(data, index)
    rec["dial_frequency"], index = get_int64(data, index)
    rec["mode"], index = get_utf8(data, index)
    rec["dx_call"], index = get_utf8(data, index)
    rec["report"], index = get_utf8(data, index)
    rec["tx_mode"], index = get_utf8(data, index)
    rec["tx_enabled"], index = get_bool(data, index)
    rec["transmitting"], index = get_bool(data, index)
    rec["decoding"], index = get_bool(data, index)
    rec["rx_df"], index = get_int32(data, index)
    rec["tx_df"], index = get_int32(data, index)
    rec["de_call"], index = get_utf8(data, index)
    rec["de_grid"], index = get_utf8(data, index)
    rec["dx_grid"], index = get_utf8(data, index)
    rec["tx_watchdog"], index = get_bool(data, index)
    rec["sub_mode"], index = get_utf8(data, index)
    rec["fast_mode"], index = get_bool(data, index)
    rec["special_operation"], index = get_int8(data, index)
    rec["freq_tolerance"], index = get_int32(data, index)
    rec["tr_period"], index = get_int32(data, index)
    rec["conf_name"], index = get_utf8(data, index)
    rec["tx_message"], index = get_utf8(data, index)
    return rec, index


def _decode_decode(rec, data, index):
    rec["packet_id"], index = get_utf8(data, index)
    rec["new"], index = get_bool(data, index)
    rec["time"], index = get_time(data, index)
    rec["snr"], index = get_int32(data, index)
    rec["delta_time"], index = get_double(data, index)
    rec["delta_frequency"], index = get_int32(data, index)
    rec["mode"] = get_utf8(data, index)
    rec["message"] = get_utf8(data, index)
    rec["low_confidence"] = get_bool(data, index)
    rec["off_air"] = get_bool(data, index)
    return rec, index


def _decode_qso(rec, data, index):
    rec["packet_id"], index = get_utf8(data, index)
    rec["time_tuple_off"], index = get_datetime_tuple(data, index)
    rec["dx_call"], index = get_utf8(data, index)
    rec["dx_grid"], index = get_utf8(data, index)
    rec["tx_freq"], index = get_int64(data, index)
    rec["mode"], index = get_utf8(data, index)
    rec["report_sent"], index = get_utf8(data, index)
    rec["report_received"], index = get_utf8(data, index)
    rec["tx_power"], index = get_utf8(data, index)
    rec["comments"], index = get_utf8(data, index)
    rec["name"], index = get_utf8(data, index)
    rec["time_tuple_on"], index = get_datetime_tuple(data, index)
    rec["operator_call"], index = get_utf8(data, index)
    rec["my_call"], index = get_utf8(data, index)
    rec["my_grid"], index = get_utf8(data, index)
    rec["exchange_sent"], index = get_utf8(data, index)
    rec["exchange_received"], index = get_utf8(data, index)
    rec["adif_propagation_mode"], index = get_utf8(data, index)
    return rec, index


def decode(data):
    packet_type_lookup = {
        0: "heartbeat",
        1: "status",
        2: "decode",
        5: "qso",
    }

    rec = {}
    index = 0

    rec["magic"], index = get_unsigned32(data, index)

    rec["schema"], index = get_unsigned32(data, index)

    packet_type_index, index = get_int32(data, index)
    rec["packet_type"] = packet_type_lookup.get(packet_type_index, "unknown")

    if rec["packet_type"] == "heartbeat":
        rec, index = _decode_heartbeat(rec, data, index)
    elif rec["packet_type"] == "status":
        rec, index = _decode_status(rec, data, index)
    elif rec["packet_type"] == "decode":
        rec, index = _decode_decode(rec, data, index)
    elif rec["packet_type"] == "qso":
        rec, index = _decode_qso(rec, data, index)
    return rec


RX_CALL = "N0CALL"
UDP_IP = "127.0.0.1"
UDP_PORT = 2237

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

while True:
    data, addr = sock.recvfrom(1024)  # Buffer size is 1024 bytes
    rec = decode(data)
    print(rec)


# class BasePacket:
#     packet_type_lookup = {
#         0: "heartbeat",
#         1: "status",
#         2: "decode",
#     }
#     serialized_fields = []

#     def __init__(self, data):
#         self.data = data
#         self.index = 0

#     @property
#     def packet_type(self):
#         return self.packet_type_lookup[self.packet_type_id]

#     def get_ordered_field_names(self):
#         descriptor_attributes = []
#         for cls in inspect.getmro(self.__class__):
#             for attr_name, attr_value in cls.__dict__.items():
#                 if isinstance(attr_value, BaseField):
#                     descriptor_attributes.append((attr_value.ordering, attr_name))
#         descriptor_attributes = [t[1] for t in sorted(descriptor_attributes)]
#         return descriptor_attributes

#     def decode(self):
#         for field in self.get_ordered_field_names():
#             getattr(self, field)
#         return self

#     def to_dict(self):
#         return {field: getattr(self, field) for field in self.serialized_fields}


# class HeartbeatPacket(BasePacket):
#     magic = Field_unsigned32(1)
#     schema = Field_unsigned32(2)
#     packet_type_id = Field_int32(3)
#     packet_id = Field_utf8(4)
#     max_schema_number = Field_int32(5)
#     version = Field_utf8(6)
#     revision = Field_utf8(7)
#     serialized_fields = [
#         "magic",
#         "schema",
#         "packet_type_id",
#         "packet_type",
#         "packet_id",
#         "max_schema_number",
#         "version",
#         "revision",
#     ]


# class StatusPacket(BasePacket):
#     magic = Field_unsigned32(1)
#     schema = Field_unsigned32(2)
#     packet_type_id = Field_int32(3)
#     packet_id = Field_utf8(4)
#     dial_frequency = Field_int64(5)
#     mode = Field_utf8(6)
#     dx_call = Field_utf8(7)
#     report = Field_utf8(8)
#     tx_mode = Field_utf8(9)
#     tx_enabled = Field_bool(10)
#     transmitting = Field_bool(11)
#     decoding = Field_bool(12)
#     rx_df = Field_int32(13)
#     tx_df = Field_int32(14)
#     de_call = Field_utf8(15)
#     de_grid = Field_utf8(16)
#     dx_grid = Field_utf8(17)
#     tx_watchdog = Field_bool(18)
#     sub_mode = Field_utf8(19)
#     fast_mode = Field_bool(20)
#     special_operation = Field_bool(21)
#     freq_tolerance = Field_int32(22)
#     tr_period = Field_int32(23)
#     conf_name = Field_utf8(24)
#     tx_message = Field_utf8(25)

#     serialized_fields = [
#         "magic",
#         "schema",
#         "packet_type_id",
#         "packet_type",
#         "packet_id",
#         "dial_frequency",
#         "mode",
#         "dx_call",
#         "report",
#         "tx_mode",
#         "tx_enabled",
#         "transmitting",
#         "decoding",
#         "rx_df",
#         "tx_df",
#         "de_call",
#         "de_grid",
#         "dx_grid",
#         "tx_watchdog",
#         "sub_mode",
#         "fast_mode",
#         "special_operation",
#         "freq_tolerance",
#         "tr_period",
#         "conf_name",
#         "tx_message",
#     ]


# def parse_packet(data):
#     magic, schema, packet_type = struct.unpack(">I I i", data[:12])

#     if magic != 0xADBCCBDA:
#         return None

#     if schema < 2:
#         raise ValueError("Schema version not supported.  Must be 2 or greater.")

#     if packet_type == 0:
#         return HeartbeatPacket(data).decode()
#     elif packet_type == 1:
#         return StatusPacket(data).decode()
#     else:
#         return None


# while True:
#     data, addr = sock.recvfrom(1024)
#     packet = parse_packet(data)
#     if packet is not None:
#         print("---")
#         print(packet.to_dict())

# # @dataclass
# # class HeartbeatPayload:
# #     packet_id: str
# #     max_schema_number: int
# #     version: str
# #     revision: str


# # @dataclass
# # class StatusPayload:


# # class Packet:
# #     packet_type_lookup = {
# #         0: "heartbeat",
# #         1: "status",
# #         2: "decode",
# #     }

# #     def __init__(self, data):
# #         self.payload = None
# #         self.is_valid = True
# #         self.data = data

# #         magic, schema, packet_type = struct.unpack(">I I i", data[:12])

# #         if magic != 0xADBCCBDA:
# #             self.is_valid = False
# #             return

# #         if schema < 2:
# #             raise ValueError("Schema version not supported.  Must be 2 or greater.")

# #         self.packet_type = self.packet_type_lookup.get(packet_type, "unknown")
# #         if self.packet_type == "unknown":
# #             self.is_valid = False

# #     def decode(self):
# #         if not self.is_valid:
# #             return

# #         if self.packet_type == "heartbeat":
# #             self._decode_heartbeat()
# #         elif self.packet_type == "status":
# #             self._decode_status()
# #         elif self.packet_type == "decode":
# #             pass
# #         else:
# #             pass

# #     def get_utf8(self, starting):
# #         length = struct.unpack(">i", self.data[starting : starting + 4])[0]
# #         message = self.data[starting + 4 : starting + 4 + length].decode("utf-8")
# #         new_index = starting + 4 + length
# #         return message, new_index

# #     def get_int32(self, starting):
# #         value = struct.unpack(">i", self.data[starting : starting + 4])[0]
# #         new_index = starting + 4
# #         return value, new_index

# #     def get_int64(self, starting):
# #         value = struct.unpack(">q", self.data[starting : starting + 8])[0]
# #         new_index = starting + 8
# #         return value, new_index

# #     def _decode_heartbeat(self):
# #         ind = 12
# #         packet_id, ind = self.get_utf8(ind)
# #         max_schema_number, ind = self.get_int32(ind)
# #         # max_schema_number = struct.unpack('>i', self.data[ind:ind + 4])[0]
# #         # ind += 4
# #         version, ind = self.get_utf8(ind)
# #         revision, ind = self.get_utf8(ind)
# #         self.payload = HeartbeatPayload(packet_id, max_schema_number, version, revision)

# #     def _decode_status(self):
# #         ind = 12
# #         packet_id, ind = self.get_utf8(ind)

# #     def __str__(self):
# #         if self.payload is not None:
# #             return f"packet_type: {self.packet_type}, payload: {self.payload}"
# #         else:
# #             return f"packet_type: {self.packet_type}"

# #     def __repr__(self) -> str:
# #         return self.__str__()


# # while True:
# #     data, addr = sock.recvfrom(1024)
# #     packet = Packet(data)
# #     packet.decode()
# #     print(packet)

# # while True:
# #     data, addr = sock.recvfrom(1024)
# #     magic, schema, packet_type = struct.unpack('>I I i', data[:12])
# #     print(f'Magic: {magic:#x}, Schema: {schema}, Packet Type: {packet_type}')


# # basefreq = 0
# # mode_type = ''
# # DXList = []
# # start_time = time.time()

# # try:

# #     while True:

# #         fileContent, addr = sock.recvfrom(1024)
# #         NewPacket = WSJTXClass.WSJTX_Packet(fileContent, 0)
# #         NewPacket.Decode()

# #         if NewPacket.PacketType == 1:
# #             StatusPacket = WSJTXClass.WSJTX_Status(fileContent, NewPacket.index)
# #             StatusPacket.Decode()
# #             basefreq = StatusPacket.Frequency

# #         elif NewPacket.PacketType == 2:

# #             if not basefreq:
# #                 continue

# #             DecodePacket = WSJTXClass.WSJTX_Decode(fileContent, NewPacket.index)
# #             DecodePacket.Decode()
# #             h = int(((DecodePacket.Time / (1000 * 60 * 60)) % 24))
# #             m = int(((DecodePacket.Time / (1000 * 60)) % 60))
# #             utc = '{:02}{:02}'.format(h, m)
# #             frequency = (int(basefreq) + int(DecodePacket.DeltaFrequency)) / 1000
# #             msg = DecodePacket.Message.split()

# #             if len(msg) > 2:
# #                 if msg[0] == "CQ":  # "CQ OX6X KP03"
# #                     mode_type = "CQ"
# #                     if len(msg[1]) < 3:  # "CQ DX/EU/NA/AS OX6X"
# #                         dx = msg[2]
# #                     else:
# #                         dx = msg[1]
# #                 else:
# #                     mode_type = "DE"
# #                     if len(msg[1]) > 2:
# #                         dx = msg[1]
# #                     else:
# #                         continue  # "73 DE OX6X"
# #             elif len(msg) == 2:
# #                 if "/" in msg[0] or "/" in msg[1]:  # "SX3X OZ/OX6X" or "OZ/OX6X SX3X"
# #                     mode_type = "DE"
# #                     if len(msg[1]) > 2:  # "OX6X/QRP 73"
# #                         dx = msg[1]
# #                     else:
# #                         continue
# #                 else:
# #                     continue
# #             else:
# #                 continue

# #             # clear unique call list every 3 minutes
# #             if time.time() - start_time > 180:
# #                 DXList = []
# #                 start_time = time.time()

# #             # only allow unique calls to be spotted during the 3-minute period
# #             if dx not in DXList:
# #                 DXList.append(dx)
# #             else:
# #                 continue

# #             spot = "{} {:<10}{:8.1f}  {:<14} {:<5}{:3} dB  {:8}{:8}{:4}Z".format(
# #                 "DX de",
# #                 (RX_CALL + "-#")[:8] + ":",
# #                 frequency,
# #                 dx,
# #                 "FT8",
# #                 DecodePacket.snr,
# #                 "",
# #                 mode_type,
# #                 utc,
# #             )

# #             print(spot)

# #             frequency = 0
# #             dx = ''
# #             mode_type = ''
# #             utc = ''

# # finally:
# #     sock.close()

# # # import socket
# # # import struct

# # # UDP_IP = "127.0.0.1"  # Change to the IP address of the WSJT-X machine if necessary
# # # UDP_PORT = 2237  # Default port for WSJT-X

# # # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# # # sock.bind((UDP_IP, UDP_PORT))

# # # print(f"Listening for WSJT-X UDP packets on {UDP_IP}:{UDP_PORT}")


# # # def parse_wsjt_message(data):
# # #     message_type = struct.unpack(">I", data[0:4])[0]
# # #     print(f'{message_type:#x}')
# # #     if message_type == 0x000000AD:
# # #         length = struct.unpack(">H", data[4:6])[0]
# # #         message_id = data[6:22]
# # #         timestamp = struct.unpack(">Q", data[22:30])[0]
# # #         snr = struct.unpack(">b", data[30:31])[0]
# # #         delta_time = struct.unpack(">f", data[31:35])[0]
# # #         delta_frequency = struct.unpack(">I", data[35:39])[0]
# # #         mode = struct.unpack(">B", data[39:40])[0]
# # #         message = data[40 : 40 + length].decode("utf-8")
# # #         print(message_id, timestamp, snr, delta_time, delta_frequency, mode, message)

# # #         return message
# # #     return None


# # # while True:
# # #     data, addr = sock.recvfrom(1024)  # Buffer size is 1024 bytes
# # #     message = parse_wsjt_message(data)
# # #     if message:
# # #         parts = message.split()
# # #         if len(parts) >= 3:
# # #             call_sign = parts[1]
# # #             grid_square = parts[2]
# # #             print(f"Call Sign: {call_sign}, Grid Square: {grid_square}")
