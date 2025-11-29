# Pulsar X3 Protocol Analysis from Capture

## Command Structure
Packets are 64 bytes. After Report ID (0x00), commands follow this pattern:
`00 [CMD1] [CMD2] [CMD3] 00 00 [VAL1] [VAL2] ...`

Checksum is 16-bit sum of bytes 0-61, stored little-endian at bytes 62-63.

## Pattern
- Write commands use `0X` in second byte position
- Query commands use `8X` in second byte (add 0x80)
- Most values use 0x01 for ON, 0x00 for OFF

## Discovered Commands

### Motion Sync
- Write ON:  `07 05 02 00 00 01 01`
- Write OFF: `07 05 02 00 00 01 00`
- Query:     `07 85 02` → byte 7 = 0/1

### Ripple Control
- Write ON:  `07 03 02 00 00 01 01`
- Write OFF: `07 03 02 00 00 01 00`
- Query:     `07 83 02` → byte 7 = 0/1

### Angle Snap
- Write ON:  `07 04 02 00 00 01 01`
- Write OFF: `07 04 02 00 00 01 00`
- Query:     `07 84 02` → byte 7 = 0/1

### LOD (Lift-off Distance)
- Write: `07 02 03 00 00 01 02 XX` (XX = mm×10: 07=0.7mm, 0a=1mm, 14=2mm)
- Query: `07 82 03` → byte 8 = mm×10

### Debounce
- Write: `04 03 03 00 00 01 XX` (XX = ms value)
- Query: `04 83 03` → byte 7 = ms value

### Battery
- Query: `08 81 01` → byte 6 = percentage

### Polling Rate
- Write: `01 09 02 00 00 01 XX`
  - Write values (powers of 2): 0x40=125Hz, 0x20=250Hz, 0x10=500Hz, 0x08=1000Hz, 0x04=2000Hz, 0x02=4000Hz, 0x01=8000Hz
- Query: `08 85 03` → byte 7 = value
  - Query values: 240=125Hz, 120=250Hz, 60=500Hz, 30=1000Hz, 15=2000Hz, 8=4000Hz, 4=8000Hz

### DPI
- Write: `05 02 05 00 00 01 [DPI_L] [DPI_H] [DPI_L] [DPI_H]`
- Query: `05 82 05` → bytes 7-8 = DPI X (little-endian), bytes 9-10 = DPI Y
- Stage query: `05 81 02` → byte 7 = current stage

### Profile
- Switch: `05 85 05 00 00 01 XX` (XX = 1-6)
