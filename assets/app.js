(function () {
  "use strict";

  const systemOrder = ["power_grid", "financial_markets", "digital_communications", "public_health", "government_response"];
  const systemLabels = {
    power_grid: "Power",
    financial_markets: "Markets",
    digital_communications: "Phones & Internet",
    public_health: "Hospitals",
    government_response: "City Offices"
  };
  const stageLabels = {
    unseen: "No alert",
    local_alarm: "Local alert",
    coordinated_response: "Citywide alert",
    emergency_powers: "Emergency rule",
    occult_task_force: "Demon task force"
  };
  const stagePolicy = {
    unseen: { repair: 2.0, detection: 1.5, possessionResistance: 2.0, containment: 0.0 },
    local_alarm: { repair: 3.5, detection: 5.0, possessionResistance: 8.0, containment: 1.2 },
    coordinated_response: { repair: 5.4, detection: 9.5, possessionResistance: 17.0, containment: 2.8 },
    emergency_powers: { repair: 7.2, detection: 15.0, possessionResistance: 28.0, containment: 4.7 },
    occult_task_force: { repair: 8.5, detection: 23.0, possessionResistance: 42.0, containment: 7.4 }
  };
  const roles = {
    tech_ceo: "Tech boss",
    plant_operator: "Power plant worker",
    political_influencer: "Public figure",
    hospital_admin: "Hospital lead",
    central_banker: "Banker"
  };

  class Generator {
    constructor(seed) {
      this.state = (seed >>> 0) || 1;
    }

    next() {
      this.state = (this.state + 0x6d2b79f5) >>> 0;
      let value = this.state;
      value = Math.imul(value ^ (value >>> 15), value | 1);
      value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
      return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
    }

    uniform(minimum, maximum) {
      return minimum + (maximum - minimum) * this.next();
    }

    snapshot() {
      return this.state >>> 0;
    }
  }

  class Simulation {
    constructor(seed, saved) {
      if (saved) {
        this.seed = saved.seed;
        this.rng = new Generator(saved.rngState);
        this.turn = saved.turn;
        this.cityName = saved.cityName;
        this.morale = saved.morale;
        this.resources = saved.resources;
        this.systems = saved.systems;
        this.npcs = saved.npcs;
        this.condition = saved.condition;
        this.threat = saved.threat;
        this.stage = saved.stage;
        this.escalations = saved.escalations || [];
        this.chronicle = saved.chronicle || [];
        this.policy = stagePolicy[this.stage];
        return;
      }

      this.seed = seed || Math.floor(Math.random() * 2147483646) + 1;
      this.rng = new Generator(this.seed);
      this.turn = 0;
      this.cityName = "New Carthage";
      this.morale = 82.0;
      this.resources = { terror: 28.0, corruption: 20.0, chaos: 14.0 };
      this.systems = defaultSystems();
      this.npcs = defaultNpcs();
      this.condition = "stable";
      this.threat = 0;
      this.stage = "unseen";
      this.policy = stagePolicy.unseen;
      this.escalations = [];
      this.chronicle = [];
    }

    serialize() {
      return {
        version: 1,
        seed: this.seed,
        rngState: this.rng.snapshot(),
        turn: this.turn,
        cityName: this.cityName,
        morale: this.morale,
        resources: this.resources,
        systems: this.systems,
        npcs: this.npcs,
        condition: this.condition,
        threat: this.threat,
        stage: this.stage,
        escalations: this.escalations.slice(-20),
        chronicle: this.chronicle.slice(-80)
      };
    }

    averageIntegrity() {
      return systemOrder.reduce((total, key) => total + this.systems[key].integrity, 0) / systemOrder.length;
    }

    averageTrust() {
      return systemOrder.reduce((total, key) => total + this.systems[key].publicTrust, 0) / systemOrder.length;
    }

    ruinScore() {
      const systemDamage = 100 - this.averageIntegrity();
      const trustDamage = 100 - this.averageTrust();
      const moraleDamage = 100 - this.morale;
      const collapsed = systemOrder.filter((key) => this.systems[key].integrity <= 25).length;
      return Math.min(100, systemDamage * 0.52 + trustDamage * 0.24 + moraleDamage * 0.20 + collapsed * 4);
    }

    isRuined() {
      return this.ruinScore() >= 88 || this.averageIntegrity() <= 18 || this.morale <= 12;
    }

    isBanished() {
      const pressure = this.policy.containment + Math.max(0, this.threat - 128) / 9;
      return this.threat >= 158 && this.resources.chaos < pressure;
    }

    perform(key, target) {
      const normalized = normalize(key);
      const command = abilities[normalized];
      if (!command) {
        throw new Error(`Don't know that move: ${key}`);
      }
      const beforeEscalations = this.escalations.length;
      const report = command.run(this, target);
      const events = report.events.slice();
      this.publish(report.events);
      const tickEvents = this.tick();
      events.push(...tickEvents);
      this.publish(tickEvents);
      return this.outcome(report.message, events, beforeEscalations, report.success !== false);
    }

    wait() {
      const beforeEscalations = this.escalations.length;
      const events = this.tick();
      this.publish(events);
      return this.outcome("You wait. The city finds a new way to fail.", events, beforeEscalations, true);
    }

    tick() {
      this.turn += 1;
      const events = [];
      const previousCondition = this.condition;
      this.condition = assessCondition(this);
      const pulse = resourcePulse(this.condition, this);
      credit(this.resources, pulse);
      events.push(event("Fear still pays", `You get Terror ${pulse.terror.toFixed(1)}, Corruption ${pulse.corruption.toFixed(1)}, and Chaos ${pulse.chaos.toFixed(1)}.`, 0, 0, pulse, null, 0, ["economy"]));
      events.push(...this.cascadeFailures());
      events.push(...this.humanResponse());
      const containment = this.containmentDrain();
      if (containment) {
        events.push(containment);
      }
      this.moveMorale();
      const detectionPressure = this.policy.detection + this.threat / 42;
      Object.values(this.npcs).forEach((npc) => tickNpc(npc, detectionPressure));
      this.condition = assessCondition(this);
      if (this.condition !== previousCondition) {
        events.push(event(`City status: ${conditionLabel(this.condition)}`, conditionDetail(this.condition), 2, 1.2, zeroDelta(), null, 0.4, ["city_state"]));
      }
      this.trim();
      return events;
    }

    cascadeFailures() {
      const events = [];
      systemOrder.forEach((sourceKey) => {
        const source = this.systems[sourceKey];
        if (failureRatio(source) < 0.24) {
          return;
        }
        Object.entries(source.coupling).forEach(([targetKey, coupling]) => {
          const target = this.systems[targetKey];
          if (target.integrity <= 0) {
            return;
          }
          const pressure = failureRatio(source) * coupling * source.volatility * (0.88 + source.strain / 150);
          if (this.rng.next() > Math.min(0.82, pressure)) {
            return;
          }
          const amount = this.rng.uniform(0.8, 3.9) * (1 + pressure * 2.1);
          const actual = damage(target, amount, 0.18);
          if (actual < 0.45) {
            return;
          }
          const delta = { terror: actual * 0.18, corruption: actual * 0.06, chaos: actual * 0.08 };
          credit(this.resources, delta);
          events.push(event(`${systemLabels[sourceKey]} breaks ${systemLabels[targetKey]}`, `${systemLabels[sourceKey]} breaks ${systemLabels[targetKey]}. Health down by ${actual.toFixed(1)}.`, actual / 3.2, actual / 2.7, delta, targetKey, actual / 8.5, ["cascade"]));
        });
      });
      return events;
    }

    humanResponse() {
      const government = this.systems.government_response;
      const events = [];
      const legitimacy = Math.max(0.22, (government.integrity + government.publicTrust) / 200);
      const repairBudget = this.policy.repair * responseMultiplier(this.condition) * legitimacy;
      systemOrder
        .slice()
        .sort((a, b) => this.systems[a].integrity - this.systems[b].integrity)
        .slice(0, 3)
        .forEach((key, index) => {
          const system = this.systems[key];
          if (system.integrity >= 95) {
            return;
          }
          const restored = repair(system, repairBudget / (index + 1));
          if (restored < 0.45) {
            return;
          }
          events.push(event(`Crews patch ${systemLabels[key]}`, `Fixed ${restored.toFixed(1)} health.`, 0, 0.25, zeroDelta(), key, 0, ["response"]));
        });
      return events;
    }

    containmentDrain() {
      if (this.policy.containment <= 0) {
        return null;
      }
      const drain = {
        terror: -this.policy.containment * 0.08,
        corruption: -this.policy.containment * 0.16,
        chaos: -this.policy.containment * 0.22
      };
      const before = JSON.stringify(this.resources);
      credit(this.resources, drain);
      if (before === JSON.stringify(this.resources)) {
        return null;
      }
      return event("Police push back", `Police took ${(-drain.terror).toFixed(1)} Terror, ${(-drain.corruption).toFixed(1)} Corruption, and ${(-drain.chaos).toFixed(1)} Chaos.`, 0, 0, drain, null, 0, ["response", "containment"]);
    }

    moveMorale() {
      const integrityGap = Math.max(0, 72 - this.averageIntegrity()) / 30;
      const trustGap = Math.max(0, 70 - this.averageTrust()) / 42;
      const pressure = integrityGap + trustGap + this.threat / 1050;
      const recovery = this.averageIntegrity() > 78 && this.averageTrust() > 70 ? 0.18 : 0;
      this.morale = clamp(this.morale - pressure + recovery);
    }

    publish(events) {
      events.forEach((item) => {
        this.chronicle.push(`Turn ${this.turn}: ${item.title} - ${item.detail}`);
        if (!item.tags.includes("response") && !item.tags.includes("economy")) {
          this.raiseThreat(publicPressure(item));
        }
      });
      this.trim();
    }

    raiseThreat(amount) {
      this.threat = Math.max(0, this.threat + amount);
      const next = stageForScore(this.threat);
      if (next === this.stage) {
        return;
      }
      const previous = this.stage;
      this.stage = next;
      this.policy = stagePolicy[next];
      this.escalations.push(escalationCopy(previous, next));
    }

    outcome(message, events, beforeEscalations, success) {
      return {
        message,
        events,
        escalations: this.escalations.slice(beforeEscalations),
        victory: this.isRuined(),
        banished: this.isBanished(),
        success
      };
    }

    trim() {
      this.chronicle = this.chronicle.slice(-80);
      this.escalations = this.escalations.slice(-20);
    }
  }

  const abilities = {
    blackout: {
      name: "Blackout",
      cost: { corruption: 2, chaos: 5 },
      target: "-",
      summary: "Cut the power. Other systems may fail too.",
      run(sim) {
        pay(sim, this.cost, this.name);
        const amount = sim.rng.uniform(16, 27) * resistance(sim, "power_grid");
        const actual = damage(sim.systems.power_grid, amount, 0.35);
        const comms = damage(sim.systems.digital_communications, actual * 0.18, 0.16);
        const delta = { terror: 6 + actual * 0.36, corruption: 1.1, chaos: 2.2 + comms * 0.08 };
        credit(sim.resources, delta);
        return {
          message: "The lights go out. Your slideshow can wait.",
          events: [event("Blackout", `Power health falls by ${actual.toFixed(1)}. Phone and internet health drops by ${comms.toFixed(1)}.`, 6 + actual / 3.4, 6.5 + actual / 4, delta, "power_grid", 4.5, ["ability", "power"])]
        };
      }
    },
    market_panic: {
      name: "Market Panic",
      cost: { corruption: 5, chaos: 2 },
      target: "-",
      summary: "Rattle the markets and the city office at once.",
      run(sim) {
        pay(sim, this.cost, this.name);
        const amount = sim.rng.uniform(14, 24) * resistance(sim, "financial_markets");
        const actual = damage(sim.systems.financial_markets, amount, 0.52);
        const gov = damage(sim.systems.government_response, actual * 0.16, 0.22);
        const delta = { terror: 3.5 + actual * 0.22, corruption: 3 + actual * 0.14, chaos: 1.4 };
        credit(sim.resources, delta);
        return {
          message: "The market panics. The anchors pretend it's fine.",
          events: [event("Market panic", `Market health falls by ${actual.toFixed(1)}. City offices lose ${gov.toFixed(1)} health.`, 5 + actual / 3.8, 7 + actual / 5, delta, "financial_markets", 3.6, ["ability", "finance"])]
        };
      }
    },
    signal_haunting: {
      name: "Signal Haunting",
      cost: { terror: 2, chaos: 4 },
      target: "-",
      summary: "Make the city's phones and networks act haunted.",
      run(sim) {
        pay(sim, this.cost, this.name);
        const actual = damage(sim.systems.digital_communications, sim.rng.uniform(13, 23) * resistance(sim, "digital_communications"), 0.48);
        const compromised = compromise(sim.systems.digital_communications, sim.rng.uniform(4, 8));
        sim.morale = Math.max(0, sim.morale - actual * 0.08);
        const delta = { terror: 4.2 + actual * 0.31, corruption: 2.7 + compromised * 0.2, chaos: 1.6 };
        credit(sim.resources, delta);
        return {
          message: "The network works. It just sends weird stuff now.",
          events: [event("Signal haunting", `Phone and internet health falls by ${actual.toFixed(1)}. Security drops by ${compromised.toFixed(1)}.`, 4.8 + actual / 4, 8 + actual / 4.2, delta, "digital_communications", 4.2, ["ability", "communications"])]
        };
      }
    },
    miasma: {
      name: "Rumor Wave",
      cost: { terror: 4, corruption: 3 },
      target: "-",
      summary: "Spread a rumor about a new outbreak.",
      run(sim) {
        pay(sim, this.cost, this.name);
        const health = damage(sim.systems.public_health, sim.rng.uniform(12, 22) * resistance(sim, "public_health"), 0.46);
        const gov = damage(sim.systems.government_response, health * 0.20, 0.30);
        sim.morale = Math.max(0, sim.morale - health * 0.12);
        const delta = { terror: 5.2 + health * 0.34, corruption: 2.1, chaos: 1.1 + gov * 0.08 };
        credit(sim.resources, delta);
        return {
          message: "People rush the hospital. Nobody trusts the all-clear.",
          events: [event("Rumors spread", `Hospital health falls by ${health.toFixed(1)}. City offices lose ${gov.toFixed(1)} health.`, 5.2 + health / 3.6, 6.2 + health / 4.5, delta, "public_health", 3.9, ["ability", "health"])]
        };
      }
    },
    paralysis: {
      name: "Office Gridlock",
      cost: { corruption: 7, chaos: 2 },
      target: "-",
      summary: "Keep city offices arguing instead of fixing things.",
      run(sim) {
        pay(sim, this.cost, this.name);
        const damageTaken = damage(sim.systems.government_response, sim.rng.uniform(15, 25) * resistance(sim, "government_response"), 0.56);
        const compromised = compromise(sim.systems.government_response, sim.rng.uniform(5, 9));
        const delta = { terror: 2.6 + damageTaken * 0.18, corruption: 4.2 + compromised * 0.25, chaos: 1.8 };
        credit(sim.resources, delta);
        return {
          message: "Every office has a plan. None of them match.",
          events: [event("Office gridlock", `City office health falls by ${damageTaken.toFixed(1)}. Security drops by ${compromised.toFixed(1)}.`, 5 + damageTaken / 3.9, 5 + damageTaken / 5.1, delta, "government_response", 3.1, ["ability", "government"])]
        };
      }
    },
    surge: {
      name: "Chaos Surge",
      cost: { terror: 8, corruption: 5 },
      target: "-",
      summary: "Trade fear and corruption for Chaos.",
      run(sim) {
        pay(sim, this.cost, this.name);
        const instability = Math.max(0, 100 - sim.averageIntegrity()) / 100;
        const chaosGain = 8 + instability * 9 + sim.rng.uniform(0, 3);
        const delta = { terror: 0, corruption: 0, chaos: chaosGain };
        credit(sim.resources, delta);
        return {
          message: "One bad day. Plenty of Chaos.",
          events: [event("Chaos surge", `Chaos rises by ${chaosGain.toFixed(1)}.`, 1.8 + chaosGain / 8, 1, delta, null, 1, ["ability", "economy"])]
        };
      }
    },
    possess: {
      name: "Take Over",
      cost: { corruption: 6, chaos: 3 },
      target: "npc-key",
      summary: "Try to take over a person with power.",
      run(sim, target) {
        const npc = targetNpc(sim, target);
        if (npc.possessed) {
          throw new Error(`${npc.name} is already under your control.`);
        }
        pay(sim, this.cost, this.name);
        const chance = possessionChance(npc, sim.resources.corruption, sim.resources.chaos, sim.policy.possessionResistance);
        const roll = sim.rng.next();
        if (roll <= chance) {
          npc.possessed = true;
          npc.suspicion = Math.min(100, npc.suspicion + 12);
          npc.cooldown = 1;
          const delta = { terror: 0, corruption: 1.5, chaos: 0.8 };
          credit(sim.resources, delta);
          return {
          message: `${npc.name} is yours now. Their 3 p.m. meeting is still on.`,
            events: [event(`${npc.name} is under your control`, `${roles[npc.role]} taken over. Chance: ${Math.round(chance * 100)}%.`, 4.5, 1.8 + npc.suspicion / 28, delta, null, 2.8, ["ability", "possession"])]
          };
        }
        npc.suspicion = Math.min(100, npc.suspicion + 18);
        return {
          message: `${npc.name} says no. They know something's wrong.`,
          success: false,
          events: [event(`${npc.name} caught on`, `Chance was ${Math.round(chance * 100)}%. The try failed.`, 2.8, 2 + npc.suspicion / 26, zeroDelta(), null, 3.2, ["ability", "possession", "failed"])]
        };
      }
    },
    exploit: {
      name: "Pull Strings",
      cost: { chaos: 2 },
      target: "npc-key",
      summary: "Use someone you took over to damage city systems.",
      run(sim, target) {
        const npc = targetNpc(sim, target);
        if (!npc.possessed) {
          throw new Error(`You haven't taken over ${npc.name} yet.`);
        }
        if (npc.cooldown > 0) {
          throw new Error(`Wait ${npc.cooldown} more turn(s) before using ${npc.name} again.`);
        }
        pay(sim, this.cost, this.name);
        const events = [];
        let totalDamage = 0;
        Object.entries(npc.influence).forEach(([key, influence]) => {
          const base = sim.rng.uniform(8.5, 15.5) * influence;
          const actual = damage(sim.systems[key], base * resistance(sim, key), 0.42);
          totalDamage += actual;
          events.push(event(`${systemLabels[key]} takes a hit`, `${npc.name} cuts its health by ${actual.toFixed(1)}.`, 4.2 + actual / 4, 3 + actual / 5.5 + npc.suspicion / 45, zeroDelta(), key, 2.2 + actual / 9.5, ["ability", "infiltration"]));
        });
        npc.suspicion = Math.min(100, npc.suspicion + 21);
        npc.cooldown = 2;
        sim.morale = Math.max(0, sim.morale - totalDamage * 0.05);
        const delta = { terror: 3.5 + totalDamage * 0.22, corruption: 2.4, chaos: 2 };
        credit(sim.resources, delta);
        const flavor = exploitFlavor(npc.role);
        events.push(event(flavor[0], flavor[1], 3.4, 4, delta, null, 1.4, ["ability", "infiltration", npc.role]));
        return {
          message: `${npc.name} uses the job to mess with city systems.`,
          events
        };
      }
    }
  };

  function defaultSystems() {
    return {
      power_grid: makeSystem("power_grid", 91, 84, 72, 1.12, { digital_communications: 0.46, public_health: 0.34, financial_markets: 0.28 }),
      financial_markets: makeSystem("financial_markets", 88, 79, 81, 1.28, { government_response: 0.39, public_health: 0.24, digital_communications: 0.31 }),
      digital_communications: makeSystem("digital_communications", 93, 82, 74, 1.34, { financial_markets: 0.43, government_response: 0.37, public_health: 0.19 }),
      public_health: makeSystem("public_health", 86, 86, 70, 1.05, { government_response: 0.42, financial_markets: 0.27, power_grid: 0.22 }),
      government_response: makeSystem("government_response", 83, 72, 76, 1.18, { power_grid: 0.25, financial_markets: 0.32, digital_communications: 0.38, public_health: 0.35 })
    };
  }

  function defaultNpcs() {
    return {
      tech_ceo: makeNpc("tech_ceo", "Mara Voss", "tech_ceo", 54, 12, { digital_communications: 1.35, financial_markets: 0.62 }),
      grid_operator: makeNpc("grid_operator", "Elias Thorn", "plant_operator", 61, 9, { power_grid: 1.42, public_health: 0.44 }),
      civic_firebrand: makeNpc("civic_firebrand", "Lenox Vale", "political_influencer", 48, 18, { government_response: 1.18, digital_communications: 0.86 }),
      hospital_admin: makeNpc("hospital_admin", "Dr. Selene Crowe", "hospital_admin", 58, 7, { public_health: 1.32, government_response: 0.41 }),
      central_banker: makeNpc("central_banker", "Oren Black", "central_banker", 64, 11, { financial_markets: 1.45, government_response: 0.53 })
    };
  }

  function makeSystem(key, integrity, publicTrust, security, volatility, coupling) {
    return { key, integrity, publicTrust, security, volatility, coupling, strain: 0 };
  }

  function makeNpc(key, name, role, willpower, suspicion, influence) {
    return { key, name, role, willpower, suspicion, influence, possessed: false, cooldown: 0 };
  }

  function damage(system, amount, trustFactor) {
    const previous = system.integrity;
    system.integrity = clamp(system.integrity - Math.max(0, amount));
    const actual = previous - system.integrity;
    system.publicTrust = clamp(system.publicTrust - actual * trustFactor * system.volatility);
    system.strain = clamp(system.strain + actual * 0.4, 0, 200);
    return actual;
  }

  function compromise(system, amount) {
    const previous = system.security;
    system.security = clamp(system.security - Math.max(0, amount));
    system.publicTrust = clamp(system.publicTrust - amount * 0.18);
    return previous - system.security;
  }

  function repair(system, amount) {
    const clean = Math.max(0, amount);
    if (!clean) {
      return 0;
    }
    const previous = system.integrity;
    system.integrity = clamp(system.integrity + clean * (0.62 + system.security / 250));
    system.publicTrust = clamp(system.publicTrust + clean * 0.12);
    system.strain = Math.max(0, system.strain - clean * 0.8);
    return system.integrity - previous;
  }

  function credit(resources, delta) {
    resources.terror = Math.max(0, resources.terror + (delta.terror || 0));
    resources.corruption = Math.max(0, resources.corruption + (delta.corruption || 0));
    resources.chaos = Math.max(0, resources.chaos + (delta.chaos || 0));
  }

  function pay(sim, cost, reason) {
    const terror = cost.terror || 0;
    const corruption = cost.corruption || 0;
    const chaos = cost.chaos || 0;
    if (sim.resources.terror + 1e-9 < terror || sim.resources.corruption + 1e-9 < corruption || sim.resources.chaos + 1e-9 < chaos) {
      throw new Error(`Need ${costText(cost)}. You have ${resourceText(sim.resources)}.`);
    }
    credit(sim.resources, { terror: -terror, corruption: -corruption, chaos: -chaos });
  }

  function event(title, detail, severity, visibility, delta, subsystem, threatDelta, tags) {
    return {
      title,
      detail,
      severity,
      visibility,
      delta: normalizeDelta(delta),
      subsystem,
      threatDelta,
      tags
    };
  }

  function normalizeDelta(delta) {
    return {
      terror: delta.terror || 0,
      corruption: delta.corruption || 0,
      chaos: delta.chaos || 0
    };
  }

  function zeroDelta() {
    return { terror: 0, corruption: 0, chaos: 0 };
  }

  function publicPressure(item) {
    return Math.max(0, item.visibility * 0.55 + item.severity * 0.85 + item.threatDelta);
  }

  function failureRatio(system) {
    return (100 - system.integrity) / 100;
  }

  function resistance(sim, key) {
    const system = sim.systems[key];
    const responseDrag = sim.policy.containment * 0.018;
    const securityDrag = system.security / 260;
    return Math.max(0.52, 1.16 - responseDrag - securityDrag);
  }

  function possessionChance(npc, corruption, chaos, responseResistance) {
    const pressure = corruption * 0.72 + chaos * 0.42;
    const defense = npc.willpower + npc.suspicion + responseResistance + (npc.possessed ? 18 : 0);
    return Math.min(0.92, Math.max(0.06, pressure / (pressure + defense + 16)));
  }

  function tickNpc(npc, detectionPressure) {
    if (npc.cooldown > 0) {
      npc.cooldown -= 1;
    }
    if (npc.possessed) {
      npc.suspicion = Math.min(100, npc.suspicion + detectionPressure * 0.16);
      if (npc.suspicion >= 96) {
        npc.possessed = false;
        npc.cooldown = 3;
      }
      return;
    }
    npc.suspicion = Math.max(0, npc.suspicion - 1.15 + detectionPressure * 0.04);
  }

  function assessCondition(sim) {
    const integrity = sim.averageIntegrity();
    const trust = sim.averageTrust();
    if (integrity <= 34 || sim.morale <= 27) {
      return "ruined";
    }
    if (integrity <= 53 || trust <= 45 || sim.morale <= 48) {
      return "crisis";
    }
    if (integrity <= 73 || trust <= 65 || sim.morale <= 68) {
      return "strained";
    }
    return "stable";
  }

  function conditionLabel(key) {
    return {
      stable: "Holding",
      strained: "Rough",
      crisis: "Crisis",
      ruined: "Ruined"
    }[key];
  }

  function conditionDetail(key) {
    return {
      stable: "Things seem normal. Mostly.",
      strained: "Little things keep going wrong.",
      crisis: "The city is in trouble. Everyone knows it.",
      ruined: "Most of the city has stopped working."
    }[key];
  }

  function responseMultiplier(key) {
    return {
      stable: 1.0,
      strained: 0.92,
      crisis: 0.78,
      ruined: 0.48
    }[key];
  }

  function resourcePulse(condition, sim) {
    if (condition === "strained") {
      const trustLoss = Math.max(0, 100 - sim.averageTrust());
      return { terror: 2.4, corruption: 1.2 + trustLoss / 90, chaos: 0.9 };
    }
    if (condition === "crisis") {
      const damageTaken = Math.max(0, 100 - sim.averageIntegrity());
      return { terror: 3.8 + damageTaken / 60, corruption: 1.9, chaos: 1.8 };
    }
    if (condition === "ruined") {
      return { terror: 5.6, corruption: 2.5, chaos: 3.4 };
    }
    return { terror: 1.2, corruption: 0.7, chaos: 0.4 };
  }

  function stageForScore(score) {
    if (score >= 118) {
      return "occult_task_force";
    }
    if (score >= 84) {
      return "emergency_powers";
    }
    if (score >= 52) {
      return "coordinated_response";
    }
    if (score >= 24) {
      return "local_alarm";
    }
    return "unseen";
  }

  function escalationCopy(previous, current) {
    const copy = {
      local_alarm: `${stageLabels[current]}: Police and repair crews are looking around.`,
      coordinated_response: `${stageLabels[current]}: Police and state teams are working together.`,
      emergency_powers: `${stageLabels[current]}: The city locks down key systems. Your job gets harder.`,
      occult_task_force: `${stageLabels[current]}: A team knows this is not human. That's bad.`,
      unseen: `${stageLabels[current]}: The city lost your trail.`
    };
    return copy[current];
  }

  function targetNpc(sim, target) {
    if (!target) {
      throw new Error("Add a person's key. Try `npcs` to see the list.");
    }
    const key = normalize(target);
    const npc = sim.npcs[key];
    if (!npc) {
      throw new Error(`Can't find '${target}'. Try \`npcs\` to see the keys.`);
    }
    return npc;
  }

  function exploitFlavor(role) {
    return {
      tech_ceo: ["Leaked CEO message", "One memo rattles the market."],
      plant_operator: ["Repair delay", "One switch gets flipped. The repair crew is stuck."],
      political_influencer: ["Rumor spreads", "One post turns a rumor into a fight."],
      hospital_admin: ["Hospital panic", "One bad update sends the hospital into a panic."],
      central_banker: ["Bank warning", "One careful statement starts a loud week."]
    }[role];
  }

  function statusText(sim) {
    const lines = [
      `${sim.cityName} | Turn ${sim.turn} | Run ${sim.seed}`,
      `City: ${conditionLabel(sim.condition)} | Police: ${stageLabels[sim.stage]} (${sim.threat.toFixed(1)})`,
      `Ruin: ${sim.ruinScore().toFixed(1)}/100 | Mood: ${sim.morale.toFixed(1)}/100`,
      `You have: ${resourceText(sim.resources)}`,
      "",
      table(["System", "Health", "Trust", "Security", "State"], systemOrder.map((key) => {
        const system = sim.systems[key];
        return [systemLabels[key], system.integrity.toFixed(1), system.publicTrust.toFixed(1), system.security.toFixed(1), statusBand(system)];
      }))
    ];
    const possessed = Object.values(sim.npcs).filter((npc) => npc.possessed);
    if (possessed.length) {
      lines.push("", `People under your control: ${possessed.map((npc) => `${npc.name} (${npc.key}, suspicion ${npc.suspicion.toFixed(0)})`).join(", ")}`);
    }
    if (sim.escalations.length) {
      lines.push("", `Police: ${sim.escalations[sim.escalations.length - 1]}`);
    }
    return lines.join("\n");
  }

  function abilityText() {
    return table(["Key", "Cost", "Person", "What it does"], Object.entries(abilities).map(([key, ability]) => [key, costText(ability.cost), ability.target === "npc-key" ? "person key" : "-", ability.summary]));
  }

  function npcText(sim) {
    return table(["Key", "Name", "Job", "State", "Alert", "Wait", "Systems"], Object.values(sim.npcs).map((npc) => {
      const influence = Object.entries(npc.influence).map(([key, value]) => `${systemLabels[key]} x${formatCompact(value)}`).join(", ");
      return [npc.key, npc.name, roles[npc.role], npc.possessed ? "under control" : "free", npc.suspicion.toFixed(0), String(npc.cooldown), influence];
    }));
  }

  function outcomeText(outcome, sim) {
    const lines = [outcome.message];
    outcome.escalations.forEach((line) => lines.push("", `Police response: ${line}`));
    outcome.events.filter(isNotable).slice(0, 9).forEach((item) => {
      lines.push(`- ${item.title}: ${item.detail}${deltaText(item.delta)}`);
    });
    if (outcome.victory) {
      lines.push("", "The city is yours. Most people had a worse night.");
    } else if (outcome.banished) {
      lines.push("", "They caught you. Your run is over.");
    }
    lines.push("", `Police ${sim.threat.toFixed(1)} (${stageLabels[sim.stage]}) | Ruin ${sim.ruinScore().toFixed(1)}/100 | ${resourceText(sim.resources)}`);
    return lines.join("\n");
  }

  function helpText() {
    return [
      "Commands",
      "status                 show the city",
      "abilities              list moves and costs",
      "npcs                   list people and their keys",
      "cast <move> [person]   use a move",
      "possess <person>       take over a person",
      "exploit <person>       use them to break systems",
      "wait                   pass a turn",
      "save                   save this run",
      "load                   load a saved run",
      "export                 download a save",
      "import                 load a save file",
      "new [number]           start a new run",
      "demo                   play a short example",
      "clear                  clear the terminal",
      "about                  learn the rules"
    ].join("\n");
  }

  function aboutText() {
    return [
      "Pandemonium: Modern Ruin",
      "Take over people. Break city systems. Don't get caught.",
      "",
      "Your run stays in this browser."
    ].join("\n");
  }

  function table(headers, rows) {
    const widths = headers.map((header, index) => Math.max(header.length, ...rows.map((row) => String(row[index]).length)));
    const headerLine = headers.map((header, index) => header.padEnd(widths[index])).join(" | ");
    const divider = widths.map((width) => "-".repeat(width)).join("-+-");
    const body = rows.map((row) => row.map((cell, index) => String(cell).padEnd(widths[index])).join(" | "));
    return [headerLine, divider, ...body].join("\n");
  }

  function statusBand(system) {
    if (system.integrity >= 76) {
      return "working";
    }
    if (system.integrity >= 51) {
      return "strained";
    }
    if (system.integrity >= 26) {
      return "failing";
    }
    return "collapsed";
  }

  function costText(cost) {
    const parts = [];
    if (cost.terror) parts.push(`${formatCompact(cost.terror)} Terror`);
    if (cost.corruption) parts.push(`${formatCompact(cost.corruption)} Corruption`);
    if (cost.chaos) parts.push(`${formatCompact(cost.chaos)} Chaos`);
    return parts.length ? parts.join(", ") : "Free";
  }

  function resourceText(resources) {
    return `Terror ${resources.terror.toFixed(1)}, Corruption ${resources.corruption.toFixed(1)}, Chaos ${resources.chaos.toFixed(1)}`;
  }

  function deltaText(delta) {
    const parts = [];
    Object.entries(delta).forEach(([key, value]) => {
      if (Math.abs(value) > 0.005) {
        parts.push(`${value > 0 ? "+" : ""}${value.toFixed(1)} ${titleCase(key)}`);
      }
    });
    return parts.length ? ` (${parts.join(", ")})` : "";
  }

  function isNotable(item) {
    return item.severity > 0 || item.visibility > 0 || Object.values(item.delta).some((value) => Math.abs(value) > 0.005);
  }

  function titleCase(value) {
    return value.charAt(0).toUpperCase() + value.slice(1);
  }

  function normalize(value) {
    return String(value || "").trim().toLowerCase().replace(/-/g, "_");
  }

  function clamp(value, lower = 0, upper = 100) {
    return Math.min(upper, Math.max(lower, value));
  }

  function formatCompact(value) {
    return Number.isInteger(value) ? String(value) : value.toPrecision(2).replace(/\.0$/, "");
  }

  const output = document.getElementById("terminal-output");
  const form = document.getElementById("terminal-form");
  const input = document.getElementById("terminal-input");
  const importFile = document.getElementById("import-file");
  const storeKey = "pandemonium-modern-ruin-save";
  let sim = new Simulation(666);
  let history = [];
  let historyIndex = 0;

  const terminal = document.querySelector(".terminal-window");
  if (terminal && window.matchMedia("(pointer: fine)").matches) {
    terminal.addEventListener("pointermove", (eventObject) => {
      const bounds = terminal.getBoundingClientRect();
      terminal.style.setProperty("--spotlight-x", `${eventObject.clientX - bounds.left}px`);
      terminal.style.setProperty("--spotlight-y", `${eventObject.clientY - bounds.top}px`);
    });
    terminal.addEventListener("pointerleave", () => {
      terminal.style.setProperty("--spotlight-x", "72%");
      terminal.style.setProperty("--spotlight-y", "18%");
    });
  }

  function write(text, tone = "system") {
    const entry = document.createElement("pre");
    entry.className = `entry ${tone}`;
    entry.textContent = text;
    output.appendChild(entry);
    output.scrollTop = output.scrollHeight;
  }

  function clearTerminal() {
    output.replaceChildren();
  }

  function refreshHud() {
    document.getElementById("signal-threat").textContent = sim.threat.toFixed(1);
    document.getElementById("signal-ruin").textContent = sim.ruinScore().toFixed(1);
    document.getElementById("signal-turn").textContent = sim.turn;
    document.getElementById("meter-terror").textContent = sim.resources.terror.toFixed(1);
    document.getElementById("meter-corruption").textContent = sim.resources.corruption.toFixed(1);
    document.getElementById("meter-chaos").textContent = sim.resources.chaos.toFixed(1);
    document.getElementById("meter-condition").textContent = conditionLabel(sim.condition);
    document.getElementById("meter-morale").textContent = sim.morale.toFixed(1);
    document.getElementById("meter-response").textContent = stageLabels[sim.stage];
    const bars = document.getElementById("subsystem-bars");
    bars.replaceChildren(...systemOrder.map((key) => {
      const system = sim.systems[key];
      const wrapper = document.createElement("div");
      wrapper.className = "system-line";
      const top = document.createElement("div");
      top.className = "system-top";
      const label = document.createElement("span");
      label.textContent = systemLabels[key];
      const value = document.createElement("span");
      value.textContent = `${system.integrity.toFixed(1)} / ${statusBand(system)}`;
      const bar = document.createElement("div");
      bar.className = "bar";
      const fill = document.createElement("span");
      fill.style.setProperty("--value", `${system.integrity}%`);
      top.append(label, value);
      bar.append(fill);
      wrapper.append(top, bar);
      return wrapper;
    }));
  }

  function execute(raw) {
    const command = raw.trim();
    if (!command) {
      return;
    }
    write(`user@ruin:~$ ${command}`, "command");
    const parts = command.split(/\s+/);
    const verb = normalize(parts[0]);
    try {
      if (verb === "status") {
        write(statusText(sim));
      } else if (verb === "abilities") {
        write(abilityText());
      } else if (verb === "npcs") {
        write(npcText(sim));
      } else if (verb === "help") {
        write(helpText());
      } else if (verb === "about") {
        write(aboutText());
      } else if (verb === "cast") {
        if (!parts[1]) {
          throw new Error("Try: cast <move> [person]");
        }
        write(outcomeText(sim.perform(parts[1], parts[2]), sim), "event");
      } else if (verb === "possess") {
        write(outcomeText(sim.perform("possess", parts[1]), sim), "event");
      } else if (verb === "exploit") {
        write(outcomeText(sim.perform("exploit", parts[1]), sim), "event");
      } else if (verb === "wait") {
        write(outcomeText(sim.wait(), sim), "event");
      } else if (verb === "save") {
        localStorage.setItem(storeKey, JSON.stringify(sim.serialize()));
        write("Run saved in this browser.", "success");
      } else if (verb === "load") {
        const saved = localStorage.getItem(storeKey);
        if (!saved) {
          throw new Error("No saved run yet.");
        }
        sim = new Simulation(null, JSON.parse(saved));
        write("Saved run loaded.", "success");
        write(statusText(sim));
      } else if (verb === "export") {
        exportSave();
        write("Save file downloaded.", "success");
      } else if (verb === "import") {
        importFile.click();
      } else if (verb === "new") {
        const seed = parts[1] ? Number.parseInt(parts[1], 10) : 666;
        if (!Number.isFinite(seed)) {
          throw new Error("Use a number for the seed.");
        }
        sim = new Simulation(seed);
        clearTerminal();
        boot();
      } else if (verb === "demo") {
        runDemo();
      } else if (verb === "clear") {
        clearTerminal();
      } else {
        throw new Error(`Don't know that command: ${parts[0]}`);
      }
    } catch (error) {
      write(error.message, "warning");
    } finally {
      refreshHud();
    }
  }

  function runDemo() {
    ["cast signal_haunting", "cast market_panic", "possess tech_ceo", "cast blackout"].forEach((line) => execute(line));
  }

  function exportSave() {
    const blob = new Blob([JSON.stringify(sim.serialize(), null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `pandemonium-save-turn-${sim.turn}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(link.href), 2000);
  }

  importFile.addEventListener("change", async () => {
    const file = importFile.files && importFile.files[0];
    importFile.value = "";
    if (!file) {
      return;
    }
    try {
      const payload = JSON.parse(await file.text());
      sim = new Simulation(null, payload);
      write("Save loaded.", "success");
      write(statusText(sim));
    } catch (error) {
      write(`Import failed: ${error.message}`, "warning");
    } finally {
      refreshHud();
    }
  });

  form.addEventListener("submit", (eventObject) => {
    eventObject.preventDefault();
    const command = input.value;
    input.value = "";
    if (command.trim()) {
      history.push(command);
      history = history.slice(-80);
      historyIndex = history.length;
    }
    execute(command);
  });

  input.addEventListener("keydown", (eventObject) => {
    if (eventObject.key === "ArrowUp") {
      eventObject.preventDefault();
      historyIndex = Math.max(0, historyIndex - 1);
      input.value = history[historyIndex] || "";
    } else if (eventObject.key === "ArrowDown") {
      eventObject.preventDefault();
      historyIndex = Math.min(history.length, historyIndex + 1);
      input.value = history[historyIndex] || "";
    }
  });

  document.querySelectorAll("[data-command]").forEach((button) => {
    button.addEventListener("click", () => {
      input.value = button.dataset.command;
      form.requestSubmit();
      input.focus();
    });
  });

  function boot() {
    write("Pandemonium // New Carthage city terminal", "success");
    write("Commands: help, status, abilities, npcs, cast, possess, exploit, wait.", "dim");
    write(statusText(sim));
    refreshHud();
  }

  boot();
  document.documentElement.classList.add("is-ready");
})();
