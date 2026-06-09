# aart-clock

A modular control-voltage system for visuals.

aart-clock is an opinionated TouchDesigner toolkit for generating, shaping, and routing signals that drive animation, generative art, audiovisual performance, and interactive installations.

Inspired by Eurorack, Monome, OXI One, and modular synthesis, aart-clock treats time, rhythm, envelopes, modulation, and sequencing as first-class building blocks. Instead of wiring visual behaviors directly, artists compose reusable signal networks:

```
Clock → Rhythm → Envelope → Mapping → Visual
```

The project provides a library of interoperable modules for:

- Master clocks and transport
- Phase and ramp generation
- Gates and triggers
- Envelopes and function generators
- LFOs and modulation sources
- Euclidean and probabilistic sequencing
- Signal mapping and shaping
- Color, motion, and instancing control

All modules share a common signal language built around six core types:

- **Phase**
- **Gate**
- **Trigger**
- **Value**
- **Vector**
- **Color**

The goal is to make visual systems feel like patching a modular synthesizer—composable, reusable, deterministic, and performance-oriented.

---

Built for TouchDesigner.

Designed for generative art.

Inspired by control voltage.
