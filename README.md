# Smart Parking Management System

A zone-based parking management system using magnetic field sensors, wireless communication, and automated payment processing.

## Overview

This system provides real-time monitoring and management of parking spaces, integrating:
- Magnetic field detection for vehicle presence
- Wireless communication for data transmission
- Automated payment processing via QR codes
- Barrier control for access management

## Features

### Hardware Components
- **Magnetic Sensors**: QMC5883L for vehicle detection
- **Microcontrollers**: ATmega328P (Arduino Pro Mini) for sensor nodes
- **Wireless Modules**: nRF24L01+ for low-power RF communication
- **Gateway**: ESP32 for Wi-Fi connectivity and barrier control
- **Barrier Actuator**: Electromechanical barrier with relay control

### Software Components
- **Local Server**: Node.js/Express for data processing and payment handling
- **Web Interface**: Responsive dashboard for real-time monitoring
- **Payment Integration**: VietQR code generation and processing

### Key Features
- Real-time parking space status monitoring
- Automated QR code generation for payment
- Barrier control based on payment confirmation
- Parking fee calculation based on occupancy time
- Sensor-based vehicle presence detection