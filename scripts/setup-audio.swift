import CoreAudio
import Foundation

let AGG_UID = "com.spotify-tui.multi-out"
let AGG_NAME = "Spotify TUI Multi-Out"

func getDevices() -> [AudioDeviceID] {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDevices,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    var size: UInt32 = 0
    AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &size)
    var devices = [AudioDeviceID](repeating: 0, count: Int(size) / MemoryLayout<AudioDeviceID>.size)
    AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &size, &devices)
    return devices
}

func getString(_ id: AudioDeviceID, _ selector: AudioObjectPropertySelector) -> String {
    var address = AudioObjectPropertyAddress(
        mSelector: selector,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    var value: Unmanaged<CFString>?
    var size = UInt32(MemoryLayout<Unmanaged<CFString>?>.size)
    let status = AudioObjectGetPropertyData(id, &address, 0, nil, &size, &value)
    guard status == noErr, let cf = value?.takeRetainedValue() else { return "" }
    return cf as String
}

func outputChannels(_ id: AudioDeviceID) -> Int {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyStreamConfiguration,
        mScope: kAudioDevicePropertyScopeOutput,
        mElement: kAudioObjectPropertyElementMain)
    var size: UInt32 = 0
    guard AudioObjectGetPropertyDataSize(id, &address, 0, nil, &size) == noErr else { return 0 }
    let buffer = UnsafeMutableRawPointer.allocate(byteCount: Int(size), alignment: MemoryLayout<AudioBufferList>.alignment)
    defer { buffer.deallocate() }
    guard AudioObjectGetPropertyData(id, &address, 0, nil, &size, buffer) == noErr else { return 0 }
    let list = buffer.assumingMemoryBound(to: AudioBufferList.self)
    var channels = 0
    for b in UnsafeMutableAudioBufferListPointer(list) { channels += Int(b.mNumberChannels) }
    return channels
}

func defaultOutput() -> AudioDeviceID {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDefaultOutputDevice,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    var id = AudioDeviceID(0)
    var size = UInt32(MemoryLayout<AudioDeviceID>.size)
    AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &size, &id)
    return id
}

func setDefaultOutput(_ id: AudioDeviceID) -> Bool {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDefaultOutputDevice,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    var device = id
    let size = UInt32(MemoryLayout<AudioDeviceID>.size)
    return AudioObjectSetPropertyData(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, size, &device) == noErr
}

let devices = getDevices()

// Modes:
//   swift setup-audio.swift          create Multi-Out + make it default
//   swift setup-audio.swift off      switch default output back to speakers
//   swift setup-audio.swift remove   off + delete the Multi-Out device
let mode = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "setup"

if mode == "off" || mode == "remove" {
    guard let speakers = devices.first(where: { getString($0, kAudioDevicePropertyDeviceUID) == "BuiltInSpeakerDevice" }) else {
        print("ERROR: built-in speakers not found — pick an output in Sound settings")
        exit(1)
    }
    let ok = setDefaultOutput(speakers)
    print("default output: MacBook Pro Speakers (\(ok ? "ok" : "FAILED"))")
    if mode == "remove" {
        if let agg = devices.first(where: { getString($0, kAudioDevicePropertyDeviceUID) == AGG_UID }) {
            let status = AudioHardwareDestroyAggregateDevice(agg)
            print(status == noErr ? "removed '\(AGG_NAME)'" : "ERROR: destroy failed: \(status)")
            exit(status == noErr && ok ? 0 : 1)
        }
        print("'\(AGG_NAME)' not found — nothing to remove")
    }
    exit(ok ? 0 : 1)
}

// Bail if our aggregate already exists — just make it default again.
if let existing = devices.first(where: { getString($0, kAudioDevicePropertyDeviceUID) == AGG_UID }) {
    let ok = setDefaultOutput(existing)
    print("aggregate already exists (id \(existing)); set as default: \(ok)")
    exit(ok ? 0 : 1)
}

guard let blackhole = devices.first(where: { getString($0, kAudioDevicePropertyDeviceUID).contains("BlackHole2ch") }) else {
    print("ERROR: BlackHole 2ch device not found — restart coreaudiod first")
    exit(1)
}
let blackholeUID = getString(blackhole, kAudioDevicePropertyDeviceUID)

// Master = current default output, unless it's virtual (Background Music,
// Teams, another aggregate...) — then fall back to built-in speakers.
var master = defaultOutput()
let masterUID = getString(master, kAudioDevicePropertyDeviceUID)
let virtual = ["BGMDevice", "MSLoopbackDriverDevice_UID", AGG_UID, "BlackHole"]
if virtual.contains(where: { masterUID.contains($0) }) || outputChannels(master) == 0 {
    if let builtin = devices.first(where: { getString($0, kAudioDevicePropertyDeviceUID) == "BuiltInSpeakerDevice" }) {
        master = builtin
    }
}
let realUID = getString(master, kAudioDevicePropertyDeviceUID)
let realName = getString(master, kAudioObjectPropertyName)

let description: [String: Any] = [
    kAudioAggregateDeviceNameKey as String: AGG_NAME,
    kAudioAggregateDeviceUIDKey as String: AGG_UID,
    kAudioAggregateDeviceIsStackedKey as String: 1,  // stacked = Multi-Output
    kAudioAggregateDeviceMainSubDeviceKey as String: realUID,
    kAudioAggregateDeviceSubDeviceListKey as String: [
        [kAudioSubDeviceUIDKey as String: realUID],
        [kAudioSubDeviceUIDKey as String: blackholeUID,
         kAudioSubDeviceDriftCompensationKey as String: 1],
    ],
]

var aggID = AudioObjectID(0)
let status = AudioHardwareCreateAggregateDevice(description as CFDictionary, &aggID)
guard status == noErr else {
    print("ERROR: AudioHardwareCreateAggregateDevice failed: \(status)")
    exit(1)
}
print("created '\(AGG_NAME)' (id \(aggID)): \(realName) + BlackHole 2ch")

if setDefaultOutput(aggID) {
    print("default output switched to '\(AGG_NAME)'")
} else {
    print("WARNING: created but could not set as default output — pick it in Sound settings")
}
