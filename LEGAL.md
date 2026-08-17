# Legal Analysis: Publishing MC-101 Firmware Analysis Findings from Germany

**Not legal advice.** This document summarizes the applicable legal frameworks for a
Germany-based researcher publishing analysis findings about the Roland
MC-101 firmware. Consult an IP attorney (or the CCC's Rechts-CTO) before publishing.

---

## The Roland EULA

Roland's firmware download page requires clicking "I AGREE AND WISH TO PROCEED WITH
DOWNLOAD." The linked license (standard Roland EULA, visible on their Axial site) states:

> **Section 3(a):** "You shall not modify, change, reverse engineer, decompile, or
> disassemble the SOFTWARE and the copyright notice and copyrighted logo."

The EULA is governed by California law. It explicitly prohibits reverse engineering,
decompiling, and disassembling.

**In the US**, this is a contract-based restriction. Whether it's enforceable for
interoperability research depends on jurisdiction (Ninth Circuit has been favorable:
Sony v. Connectix, Sega v. Accolade). But it's a real risk.

**In Germany/EU**, the situation is fundamentally different.

---

## EU Software Directive (2009/24/EC) — implemented in Germany as UrhG §§69a–69g

The EU Computer Programs Directive is binding law in all member states. Germany
implemented it as §§69a–69g of the Urheberrechtsgesetz (UrhG, German Copyright Act).
It provides two distinct rights:

### Article 5 / UrhG §69d — Right to observe, study, and test

> "The person having a right to use a copy of a computer program shall be entitled,
> without the authorisation of the rightholder, to observe, study or test the
> functioning of the program in order to determine the ideas and principles which
> underlie any element of the program if he does so while performing any of the acts
> of loading, displaying, running, transmitting or storing the program which he is
> entitled to do."

**Key point:** This right exists *without* the rightholder's authorization. The ECJ
(European Court of Justice) ruled in **Case C-406/10 (SAS Institute v. World
Programming, 2012)** that:

> "The owner of the copyright in a computer program may not prevent, by relying on
> the licensing agreement, the person who has obtained that licence from determining
> the ideas and principles which underlie all the elements of that program."

And:

> "To accept that the functionality of a computer program can be protected by
> copyright would amount to making it possible to monopolise ideas, to the detriment
> of technological progress and industrial development."

**Translation:** The EULA's reverse engineering prohibition is **unenforceable** under
EU/German law for the purpose of observing, studying, or testing the program. Roland
cannot use the EULA to prevent you from determining the ideas and principles
underlying the firmware.

### Article 6 / UrhG §69e — Decompilation

Decompilation (converting code to a higher-level, human-readable language) is legal
without authorization **only** for interoperability purposes, and only if:

- (a) You lawfully acquired the program (you did — downloaded from Roland's site)
- (b) The information necessary for interoperability is not already readily available
- (c) You confine decompilation to the parts necessary for interoperability

The information obtained cannot be:
- Used for purposes other than interoperability
- Given to others (except for interoperability purposes)
- Used to develop a program "substantially similar in its expression"

**CJEU Case C-13/20 (BSA v. Greenplum, October 2021)** further broadened this right,
allowing decompilation even to correct software errors.

### Disassembly vs. decompilation

The Directive defines decompilation as "the conversion of program code into a
higher-level programming language that can be read by a human." Disassembly
(converting machine code to assembly) is a borderline case — it's a weaker form than
decompilation, and assembly is arguably "human-readable." Legal analysis (see
[Vidstrom Labs](https://vidstromlabs.com/blog/the-legal-boundaries-of-reverse-engineering-in-the-eu/))
suggests disassembly is **probably legal in general** under EU law because:

1. The idea/expression dichotomy (Article 1: "Ideas and principles which underlie any
   element of a computer program, including those which underlie its interfaces, are
   not protected by copyright")
2. It's extremely difficult to fully reverse engineer a commercial product using only
   disassembly, so it doesn't threaten the developer's investment
3. The ECJ ruling in C-406/10 distinguishes between having access to source code
   (decompilation) and merely studying the program (observation) — disassembly
   sits closer to observation

---

## How this applies to our work

| What we did | EU/German legal basis | Risk |
|-------------|----------------------|------|
| Downloaded firmware from Roland's website | Lawful acquisition (required by Art. 5/6) | None |
| Observed, studied, tested the firmware (running it, probing via SysEx) | Art. 5 / UrhG §69d — explicitly legal without authorization; EULA prohibition unenforceable | None |
| Disassembled unencrypted parts (sdram1.bin) | Borderline — likely legal (see above); closer to observation than decompilation | Low |
| Analyzed structural properties of encrypted C0A without decrypting | Not decompilation, not circumvention — just structural analysis | None |
| Did NOT decrypt C0A | No anti-circumvention issue (no DMCA equivalent invoked) | None |
| Published findings (architecture, addresses, protocol structure) | Art. 1: ideas and principles are not copyright-protected; ECJ: functionality cannot be monopolized | Low |
| Published Roland's internal debug strings (e.g., "Wr(1)", "SIO#1") | Factual findings about the program's structure — ideas, not expression | Low–medium |
| Did NOT publish firmware binaries or code | No copyright infringement | None |

---

## The CCC precedent

The Chaos Computer Club (CCC), headquartered in Germany, has a 40+ year history of
publishing reverse engineering findings:

- **Staatstrojaner (2011):** The CCC reverse-engineered German government spyware and
  published a detailed technical analysis, including decompiled code fragments. No
  legal consequences — the analysis was protected as security research and journalism.
- **Annual CCC Congress:** Routinely features firmware RE, hardware hacking, and
  security analysis presentations. The CCC's legal team (Rechts-CTO) provides ongoing
  support for researchers.
- **Newag train hackers (2024–2025):** The CCC supported Polish hackers who reverse-
  engineered train manufacturer software to expose anti-competitive practices.

The CCC's position: reverse engineering for interoperability, security research,
and public interest is not only legal but constitutionally protected under German
law (Art. 5 Grundgesetz — freedom of expression, Art. 5 GG, including
Wissenschaftsfreiheit — freedom of science/research).

---

## DMCA equivalent in the EU

The EU has **Directive 2001/29/EC** (InfoSoc Directive), Article 6, which provides
anti-circumvention protections similar to the US DMCA. However:

- We did **not** circumvent any technological protection measure. We analyzed
  unencrypted parts and structural properties. We never decrypted C0A.
- The anti-circumvention provisions protect "access" to copyrighted works. We had
  lawful access to the firmware (downloaded from Roland's website). The encryption
  protects one component (C0A) that we did not access.
- Even if anti-circumvention were argued, EU law has broader research and
  interoperability exemptions than the US DMCA.

---

## Practical risk assessment for publishing from Germany

| Risk factor | Assessment |
|-------------|-----------|
| EULA breach (contract law) | **Very low.** The EULA's RE prohibition is unenforceable under EU law (ECJ C-406/10). Roland cannot rely on the licensing agreement to prevent you from studying the firmware. |
| Copyright infringement | **Very low.** The blog post publishes findings (ideas, architecture), not code (expression). The idea/expression dichotomy is explicit in EU law. |
| Trade secret misappropriation | **Low.** The information was obtained by analyzing a lawfully acquired product, not through improper means. German trade secret law (GeschGehG) requires that the secret was obtained through "unlawful means" — reverse engineering a lawfully acquired product is explicitly lawful. |
| DMCA-equivalent anti-circumvention | **Very low.** We did not circumvent any encryption. |
| Roland sending a cease-and-desist (Abmahnung) | **Possible but unlikely.** German Abmahnung culture means Roland *could* send a cease-and-desist letter. However, given the strong EU legal framework protecting RE for research, they would have weak legal grounds. The CCC's legal team has extensive experience defending against such letters. |

---

## Recommendations

1. **Publish findings, not code.** The blog post describes architecture, addresses,
   and protocol structure — not Roland's binary code or source. This is the key
   distinction that keeps you on the right side of copyright law.

2. **Do not publish the firmware binaries.** The repo already contains the extracted
   firmware files (`firmware/` directory). Consider whether these should be public.
   They are freely downloadable from Roland's website, but redistributing them could
   be argued as copyright infringement. Consider adding a note: "Firmware binaries
   are not redistributed; download from Roland's support site."

3. **Frame as interoperability research.** The EU Directive's strongest protections
   are for interoperability (Art. 6) and observation/study (Art. 5). Frame the work
   as: "This research was conducted to understand the MC-101's SysEx interface for
   interoperability with third-party tools."

4. **Add a disclaimer.** Something like: "This work was conducted for interoperability
   and security research purposes under EU Directive 2009/24/EC. No Roland firmware
   code or binaries are redistributed. Findings describe the architecture and ideas
   underlying the firmware, not its expression."

5. **Consider consulting the CCC's Rechts-CTO.** The CCC provides legal support for
   researchers in Germany. Their experience with similar cases (Staatstrojaner,
   hardware hacking at CCC Congress) makes them the best first point of contact for
   a quick legal reality check.

6. **The most sensitive content** in the blog post is the internal debug strings
   (Roland's internal codenames for parameter regions) and the test-mode dispatch
   table. These are factual findings about the program's structure (ideas), not
   expression, but if you want to be extra cautious, you could note that these were
   observed during lawful study of the firmware without redacting them.

---

## Sources

- [EU Directive 2009/24/EC](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32009L0024) (Computer Programs Directive)
- [CJEU Case C-406/10 (SAS Institute v. World Programming, 2012)](http://curia.europa.eu/juris/document/document.jsf?text=&docid=122362) — RE for functionality is fair use; EULA RE prohibitions unenforceable
- [CJEU Case C-13/20 (BSA v. Greenplum, 2021)](https://www.lexology.com/library/detail.aspx?g=f5b1193c-f423-4f96-bca5-03f514) — decompilation to correct errors is legal
- [Vidstrom Labs: Legal boundaries of RE in the EU](https://vidstromlabs.com/blog/the-legal-boundaries-of-reverse-engineering-in-the-eu/) — practical analysis of the Directive
- [EFF Coders' Rights Project RE FAQ](https://www.eff.org/issues/coders/reverse-engineering-faq) — US perspective (for comparison)
- [Roland EULA (Axial site)](https://axial.roland.com/articles/jupiter-80-synth-legends/) — full text of Roland's standard software license
- [§69e UrhG (dejure.org)](https://dejure.org/gesetze/UrhG/69e.html) — German implementation of the decompilation provision
