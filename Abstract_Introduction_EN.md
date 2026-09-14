**ZONE-BASED SMART PARKING MANAGEMENT SYSTEM**

# ABSTRACT

Traditional parking facilities largely rely on manual ticket issuance, human-operated barriers, and cash payment, which are slow, error-prone, and difficult to scale. This report presents the design of a Zone-Based Smart Parking Management System that focuses on two core capabilities: real-time, power-efficient slot occupancy monitoring, and cashless payment through dynamic VietQR codes. Each parking slot is equipped with a battery-powered wireless sensor node built around a QMC5883L three-axis magnetometer, which detects the presence of a vehicle by sensing the local distortion of the Earth's magnetic field caused by the vehicle's metal mass. Each node is controlled by a low-power microcontroller (ATmega328P) that remains in deep-sleep mode between periodic readings and communicates slot status to a central ESP32 gateway over an nRF24L01+ 2.4 GHz radio link, transmitting only when a change in occupancy is detected. This event-driven, low-duty-cycle design allows each sensor node to operate for extended periods on small batteries without requiring wired power or continuous network connectivity. The ESP32 gateway forwards slot-status updates to a Local Server, which maintains a real-time occupancy dashboard and, at the point of vehicle exit, calculates the parking fee and generates a dynamic VietQR code for immediate, cashless settlement through any participating bank application. By combining a magnetic-sensing and RF-based occupancy layer with a local, offline-first payment backend, the system offers an affordable and energy-efficient alternative to camera-based or wired sensor approaches, making it particularly suitable for small and medium-sized parking lots.

# CHAPTER 1. INTRODUCTION

## 1.1 Background and Motivation

The rapid growth of vehicle ownership in urban areas has placed increasing pressure on parking infrastructure, particularly on the ability of small and medium-sized lots to track slot availability and collect payment efficiently. Camera-based occupancy detection, while effective, requires continuous image processing, careful mounting to avoid obstruction by neighboring vehicles, and a comparatively high power budget — making it a poor fit for lots that want a low-cost, battery-friendly monitoring layer. Wired sensors, such as ultrasonic modules connected back to a central controller, avoid the processing overhead of vision-based systems but introduce significant installation cost, since cabling must be run to every monitored slot.

This project instead adopts a magnetic-sensing approach: a vehicle's chassis and engine block are large ferrous masses that measurably distort the ambient magnetic field directly above them. A small, low-power magnetometer embedded at or near each slot can detect this distortion directly, without requiring a camera, a line-of-sight sensor, or a wired power/data connection. Combined with a low-power microcontroller that spends the vast majority of its time in a deep-sleep state, and a short-range radio (nRF24L01+) that only transmits when the occupancy state actually changes, this approach allows each slot sensor to run for extended periods on small batteries. On the payment side, VietQR — Vietnam's interbank QR-code payment standard — allows any customer with a banking application to complete a transfer in seconds by scanning a dynamically generated code, removing the need for cash handling or a proprietary payment terminal.

## 1.2 Problem Statement

The central problem addressed by this project can be summarized as follows: how can a small parking facility monitor per-slot occupancy in real time using a wireless, battery-powered sensing layer that minimizes power consumption and installation cost, while integrating this data with a local server that automatically calculates parking fees and generates cashless VietQR payment codes, without relying on cameras, wired sensors, or continuous internet connectivity?

## 1.3 Objectives

The general objective of this project is to design, implement, and validate a working prototype of a zone-based parking-slot monitoring and payment system built around magnetic sensing, low-power wireless communication, and local VietQR payment processing. The specific objectives are:

1. Design a battery-powered slot-sensor node combining a QMC5883L magnetometer with a low-power microcontroller (ATmega328P) and an nRF24L01+ radio module.
2. Implement a duty-cycled firmware routine in which the node remains in deep sleep, wakes periodically to take a single magnetic-field reading, and transmits a status update only when the occupancy state changes.
3. Calibrate each sensor node against its installation environment to reliably distinguish an occupied slot from an empty one under real ambient magnetic conditions.
4. Develop an ESP32-based gateway that continuously listens for status packets from all sensor nodes and forwards updates to the Local Server.
5. Build a Local Server component that maintains real-time slot-occupancy state, calculates parking fees, and generates dynamic VietQR codes for exit payment.
6. Evaluate the power consumption of the sensor nodes to confirm the design meets the project's energy-efficiency goals.

## 1.4 Scope and Limitations

**In scope:** the design and firmware of the magnetic-sensor slot nodes, the RF communication protocol between nodes and the ESP32 gateway, the Local Server logic for occupancy tracking and VietQR fee calculation, demonstrated on a small-scale prototype covering 3 to 5 parking slots.

**Out of scope:** large-scale, multi-lot, or multi-level commercial deployment; vehicle entry/exit license-plate recognition and the lost-ticket recovery workflow, which are treated as a separate subsystem of the broader parking system; and long-term, real-world battery-life validation beyond laboratory-scale testing.

**Known limitations:** magnetic-field readings can be affected by nearby ferrous structures (rebar, metal beams), requiring per-slot calibration at installation time; the current design assumes a single shared RF channel serving 3 to 5 nodes rather than a larger, multi-channel deployment.