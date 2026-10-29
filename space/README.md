---
title: EchoProof Bank Line
emoji: 🔊
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: Voice agent where the caller hears what the screen shows
---

# EchoProof bank line

A voice agent built entirely on AssemblyAI: Sync STT hears the caller, LLM Gateway writes the
reply, **SayGuard** makes it safe to say, TTS-1 speaks it, and Sync STT checks every amount,
date, code and name inside the exact time window it was spoken.

Flip SayGuard off to hear what the caller hears without it. Code: https://github.com/cipoklean/echoproof
