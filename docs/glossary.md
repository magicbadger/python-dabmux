# Glossary

DAB and multiplexing terminology.

## A

### AAC (Advanced Audio Coding)
Audio compression codec used in DAB+. HE-AAC v2 (High-Efficiency AAC version 2) is the standard for DAB+, providing better quality at lower bitrates than MPEG Layer II.

### AF Packet (Application Fragment Packet)
Container format in EDI protocol that wraps TAG items with synchronization, sequence numbers, and CRC.

## B

### Bitrate
Data rate of an audio or data stream, measured in kilobits per second (kbps). Common DAB bitrates: 32-192 kbps for MPEG Layer II, 32-96 kbps for DAB+.

## C

### Capacity Unit (CU)
The basic unit of multiplex capacity in DAB. Mode I has 864 CU total. Each subchannel occupies a number of CUs based on its bitrate and protection level.

### Component
Link between a service and a subchannel in the ensemble configuration. One service can have multiple components (e.g., audio + data).

### CRC (Cyclic Redundancy Check)
Error detection code used throughout ETI frames and EDI packets to verify data integrity.

## D

### DAB (Digital Audio Broadcasting)
Digital radio technology standard. Originally referred to the MPEG Layer II audio variant, now encompasses both DAB and DAB+.

### DAB+
Enhanced version of DAB using HE-AAC v2 audio coding instead of MPEG Layer II. Provides better audio quality at lower bitrates.

### DMB (Digital Multimedia Broadcasting)
Data mode for transmitting multimedia content (images, text, video) over DAB.

## E

### EBU Latin
Character encoding used for DAB labels and text. Subset of UTF-8 covering common European languages.

### ECC (Extended Country Code)
8-bit code identifying the country (e.g., 0xE1 for Germany, 0xE2 for UK). Used in ensemble configuration.

### EDI (Ensemble Data Interface)
Network protocol for transmitting ETI frames over UDP or TCP. Includes TAG items, AF packets, and optional PFT.

### EEP (Equal Error Protection)
Protection scheme where all data in a subchannel has the same protection level. Alternative to UEP.

### Ensemble
Complete DAB multiplex containing multiple services. Identified by ensemble ID and label.

### ETI (Ensemble Transport Interface)
Frame format for DAB multiplex data. Contains headers, FIC data, main service channel data, and checksums. Standard frame size: 6144 bytes (Mode I).

## F

### FC (Frame Characterization)
4-byte header in ETI frame containing frame count, number of subchannels, transmission mode, and frame length.

### FEC (Forward Error Correction)
Error correction technique used in PFT to recover lost packets. python-dabmux uses Reed-Solomon codes.

### FIC (Fast Information Channel)
Data channel in ETI frame containing service information (FIGs). Size: 96 bytes for Mode I, 32 bytes for other modes.

### FIG (Fast Information Group)
Information block in FIC carrying service details, labels, and configuration. Different FIG types (0-7) carry different information.

### FIG 0/0
MCI (Multiplex Configuration Information) - Ensemble configuration.

### FIG 0/1
Subchannel organization - How subchannels are arranged in the multiplex.

### FIG 0/2
Service organization - Which components belong to which services.

### FIG 1/0
Ensemble label - Text label for the ensemble.

### FIG 1/1
Service labels - Text labels for services.

### Frame
Single time unit of DAB transmission. Mode I: 96ms, Mode II/III: 24ms, Mode IV: 96ms.

## H

### HE-AAC v2 (High-Efficiency Advanced Audio Coding version 2)
Audio codec used in DAB+. Includes Spectral Band Replication (SBR) and Parametric Stereo (PS) for efficient low-bitrate encoding.

## L

### Label
Text identifier for ensemble, service, or subchannel. Two forms: long (max 16 characters) and short (max 8 characters).

### LTO (Local Time Offset)
Time offset from UTC for the ensemble. Can be set manually or automatically.

## M

### Main Service Channel (MSC or MST)
Data area in ETI frame containing audio/data streams from all subchannels.

### MCI (Multiplex Configuration Information)
Information about ensemble configuration, transmitted via FIG 0/0.

### Mode I, II, III, IV
DAB transmission modes with different frame durations, FIC sizes, and capacities:
- Mode I: 96ms, 96-byte FIC, 864 CU (most common)
- Mode II: 24ms, 32-byte FIC, 432 CU
- Mode III: 24ms, 32-byte FIC, 864 CU
- Mode IV: 96ms, 32-byte FIC, 432 CU

### MPEG Layer II (MPEG-1 Audio Layer II)
Audio codec used in traditional DAB. Part of the MPEG-1 standard. File extension: .mp2

### MST (Main Stream Data)
See Main Service Channel.

### MTU (Maximum Transmission Unit)
Maximum packet size for network transmission. Typically 1500 bytes for Ethernet. PFT fragments larger packets to fit MTU.

### Multiplexer (Mux)
System that combines multiple audio/data streams into a single DAB ensemble (ETI frames).

## P

### Packet Mode
Data transmission mode in DAB for packet-based data services.

### PFT (Protection, Fragmentation and Transport)
EDI layer providing packet fragmentation, sequence numbers, and optional FEC (Reed-Solomon).

### Programme Type (PTY)
Classification of service content (0-31). Examples: 1=News, 10=Pop Music, 14=Classical.

### Protection Level
Error protection strength for a subchannel (0-4). Higher levels = more robust against errors but higher overhead. Level 2 is typical.

## R

### Reed-Solomon
Error correction code used in PFT FEC. Can recover lost packets based on redundancy.

## S

### Service
Radio station or data service in the ensemble. Has a unique service ID, label, programme type, and language. Listeners tune to services.

### Service ID (SId)
16-bit identifier for a service (e.g., 0x5001). Must be unique within ensemble.

### SFN (Single Frequency Network)
Multiple transmitters broadcasting the same signal on the same frequency. Requires precise timing (TIST).

### Subchannel
Data stream in the multiplex carrying audio or data. Characterized by bitrate, protection level, and start address in CUs.

### Subchannel ID (SubChId)
6-bit identifier (0-63) for a subchannel within the ensemble.

### SYNC
4-byte header at start of ETI frame containing error indicator and frame sync word (0x49C5F8).

## T

### TAG Item
Data element in EDI protocol. Types include *ptr (protocol), deti (ETI data), estN (timestamp).

### TIST (Timestamp)
Optional 4-byte timestamp in ETI frame. Used for precise timing in SFN networks. Based on 16.384 MHz clock.

### Transmission Mode
See Mode I, II, III, IV.

## U

### UDP (User Datagram Protocol)
Network protocol used for EDI streaming. Connectionless, suitable for multicast.

### UEP (Unequal Error Protection)
Protection scheme where different parts of subchannel data have different protection levels. More efficient than EEP for MPEG Layer II.

## Abbreviations

| Abbreviation | Full Term |
|--------------|-----------|
| AAC | Advanced Audio Coding |
| AF | Application Fragment |
| CRC | Cyclic Redundancy Check |
| CU | Capacity Unit |
| DAB | Digital Audio Broadcasting |
| DMB | Digital Multimedia Broadcasting |
| EBU | European Broadcasting Union |
| ECC | Extended Country Code |
| EDI | Ensemble Data Interface |
| EEP | Equal Error Protection |
| ETI | Ensemble Transport Interface |
| FC | Frame Characterization |
| FEC | Forward Error Correction |
| FIC | Fast Information Channel |
| FIG | Fast Information Group |
| HE-AAC | High-Efficiency Advanced Audio Coding |
| LTO | Local Time Offset |
| MCI | Multiplex Configuration Information |
| MSC | Main Service Channel |
| MST | Main Stream Data |
| MPEG | Moving Picture Experts Group |
| MTU | Maximum Transmission Unit |
| PFT | Protection, Fragmentation and Transport |
| PTY | Programme Type |
| SFN | Single Frequency Network |
| SId | Service Identifier |
| SubChId | Subchannel Identifier |
| TCP | Transmission Control Protocol |
| TIST | Timestamp |
| UDP | User Datagram Protocol |
| UEP | Unequal Error Protection |

## Numeric Values

### Programme Types (PTY)

| Value | Type | Description |
|-------|------|-------------|
| 0 | None | No programme type |
| 1 | News | News |
| 2 | Current Affairs | Current affairs |
| 3 | Information | General information |
| 4 | Sport | Sports |
| 5 | Education | Educational |
| 6 | Drama | Drama |
| 7 | Culture | Arts and culture |
| 8 | Science | Science |
| 9 | Varied Speech | Talk/varied speech |
| 10 | Pop Music | Pop music |
| 11 | Rock Music | Rock music |
| 12 | Easy Listening | Easy listening music |
| 13 | Light Classical | Light classical |
| 14 | Serious Classical | Serious classical |
| 15 | Other Music | Other music |
| 16 | Weather | Weather |
| 17 | Finance | Finance/business |
| 18 | Children's | Children's programmes |
| 19 | Social Affairs | Social affairs |
| 20 | Religion | Religion |
| 21 | Phone In | Phone-in |
| 22 | Travel | Travel |
| 23 | Leisure | Leisure |
| 24 | Jazz Music | Jazz |
| 25 | Country Music | Country |
| 26 | National Music | National music |
| 27 | Oldies Music | Oldies |
| 28 | Folk Music | Folk |
| 29 | Documentary | Documentary |
| 30-31 | - | Reserved |

### Language Codes (Selection)

| Value | Language |
|-------|----------|
| 0 | Unknown |
| 1 | Albanian |
| 2 | Breton |
| 3 | Catalan |
| 4 | Croatian |
| 5 | Welsh |
| 6 | Czech |
| 7 | Danish |
| 8 | German |
| 9 | English |
| 10 | Spanish |
| 11 | Esperanto |
| 12 | Estonian |
| 13 | Basque |
| 14 | Faroese |
| 15 | French |
| 16 | Frisian |
| 17 | Irish |
| 18 | Gaelic |
| 19 | Galician |
| 20 | Icelandic |
| 21 | Italian |
| 22 | Lappish |
| 23 | Latin |
| 24 | Latvian |
| 25 | Luxembourgian |
| 26 | Lithuanian |
| 27 | Hungarian |
| 28 | Maltese |
| 29 | Dutch |
| 30 | Norwegian |
| 31 | Occitan |
| 32 | Polish |
| 33 | Portuguese |
| 34 | Romanian |
| 35 | Romansh |
| 36 | Serbian |
| 37 | Slovak |
| 38 | Slovene |
| 39 | Finnish |
| 40 | Swedish |
| 41 | Turkish |
| 42 | Flemish |
| 43 | Walloon |

[See full list in ETSI EN 300 401]

### Extended Country Codes (ECC)

| Code | Country/Region |
|------|----------------|
| 0xE0 | Germany |
| 0xE1 | Algeria, Andorra, Belgium, etc. |
| 0xE2 | United Kingdom |
| 0xE3 | Czech Republic, Estonia, Greece, etc. |
| 0xE4 | Denmark, Gibraltar, etc. |
| 0xF0 | France |
| 0xF1 | Egypt, Syria, etc. |

[See full list in ETSI EN 300 401]

### Protection Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| 0 | Weakest | Very strong signal only |
| 1 | Weak | Good signal required |
| 2 | Moderate | Standard (recommended) |
| 3 | Strong | Weak signal areas |
| 4 | Strongest | Maximum robustness |

## Common Bitrates

### DAB (MPEG Layer II)

| Bitrate | Quality | Use Case |
|---------|---------|----------|
| 32 kbps | Low | Mono speech (minimal) |
| 64 kbps | Fair | Mono speech |
| 96 kbps | Good | Stereo speech, low music |
| 128 kbps | Very Good | Standard music quality |
| 160 kbps | Excellent | High-quality music |
| 192 kbps | Premium | Premium music quality |

### DAB+ (HE-AAC v2)

| Bitrate | Quality | Equivalent DAB |
|---------|---------|----------------|
| 32 kbps | Good | ~64 kbps speech |
| 48 kbps | Very Good | ~96 kbps speech |
| 64 kbps | Excellent | ~128 kbps music |
| 72 kbps | Excellent | ~128-160 kbps music |
| 96 kbps | Premium | ~192 kbps music |

## Frame Sizes and Timing

### Mode I (Most Common)

- Frame duration: 96 ms
- Frame rate: 10.416̄ frames/second
- FIC size: 96 bytes
- Total capacity: 864 CU
- ETI frame size: 6144 bytes (6148 with TIST)

### Mode II

- Frame duration: 24 ms
- Frame rate: 41.6̄ frames/second
- FIC size: 32 bytes
- Total capacity: 432 CU

### Mode III

- Frame duration: 24 ms
- Frame rate: 41.6̄ frames/second
- FIC size: 32 bytes
- Total capacity: 864 CU

### Mode IV

- Frame duration: 96 ms
- Frame rate: 10.416̄ frames/second
- FIC size: 32 bytes
- Total capacity: 432 CU

## See Also

- [ETSI EN 300 401](https://www.etsi.org/deliver/etsi_en/300400_300499/300401/) - DAB standard
- [ETSI EN 300 799](https://www.etsi.org/deliver/etsi_en/300700_300799/300799/) - ETI specification
- [FAQ](faq.md) - Frequently asked questions
- [Standards](standards/index.md) - Standards compliance
