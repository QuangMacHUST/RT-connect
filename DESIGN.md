---
name: Clinical Precision Interface
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#44474d'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#74777e'
  outline-variant: '#c4c6ce'
  surface-tint: '#4a5f7f'
  primary: '#001229'
  on-primary: '#ffffff'
  primary-container: '#0f2744'
  on-primary-container: '#798fb1'
  inverse-primary: '#b2c8ed'
  secondary: '#006a61'
  on-secondary: '#ffffff'
  secondary-container: '#86f2e4'
  on-secondary-container: '#006f66'
  tertiary: '#001323'
  on-tertiary: '#ffffff'
  tertiary-container: '#002942'
  on-tertiary-container: '#2c94d8'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d4e3ff'
  primary-fixed-dim: '#b2c8ed'
  on-primary-fixed: '#021c39'
  on-primary-fixed-variant: '#324866'
  secondary-fixed: '#89f5e7'
  secondary-fixed-dim: '#6bd8cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#005049'
  tertiary-fixed: '#cce5ff'
  tertiary-fixed-dim: '#93ccff'
  on-tertiary-fixed: '#001d31'
  on-tertiary-fixed-variant: '#004b73'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-md-medium:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  body-sm-medium:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-numeric-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  label-code-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  label-code-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
    letterSpacing: 0.02em
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.06em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  grid-gutter: 12px
  grid-margin: 16px
  space-2xs: 2px
  space-xs: 4px
  space-sm: 8px
  space-md: 12px
  space-lg: 16px
  space-xl: 20px
  space-2xl: 24px
  space-3xl: 32px
---

## Brand & Style

This design system is engineered specifically for radiation oncologists, medical physicists, and dosimetrists operating within clinical radiotherapy workflows. The environment demands zero ambiguity, uncompromising legibility under variable hospital lighting conditions, and immediate perceptual clarity when interpreting safety-critical metrics (such as dose volume histograms, gamma passing rates, and coordinate alignment).

The design philosophy unites **Clinical Minimalism** with **High-Density Technical Engineering**:
- **Tone:** Authoritative, disciplined, accurate, and calm. No decorative gradients, gratuitous glassmorphic blurs, or distracting animations.
- **Visual Weight:** Razor-sharp 1px structural boundaries, explicit state signaling, and balanced information density that maximizes screen real estate without inducing cognitive fatigue.
- **Mental Model:** A digitized clinical workstation adhering to the rigor of physical diagnostic instrumentation while offering modern web-grade ergonomics.

## Colors

The chromatic architecture prioritizes high contrast, clinical neutrality, and standardized medical status semantics:

### Primary & Functional Accents
- **Primary Navy (`#0F2744` / Dark Variant `#1E3A8A`):** Anchors primary actions, active navigational tabs, top-level brand chrome, and critical operational controls. Represents institutional authority and technical rigor.
- **Clinical Teal / Cyan (`#0D9488` / Interactive `#14B8A6`):** Applied to dose-distribution highlights, active interactive selections, secondary actions, and dosimetry metadata indicators.
- **Provenance Blue (`#0284C7`):** Reserved for technical provenance callouts, algorithm versions, guidance notes, and DICOM metadata tooltips.

### Surfaces & Structural Neutrals
- **Workstation Canvas (`#F8FAFC`):** Soft, low-strain clinical background supporting extended viewing sessions.
- **Panel Surface (`#FFFFFF`):** High-clarity elevated cards, data panels, and viewer wrappers.
- **Muted Section Fill (`#F1F5F9`):** Sub-headers, disabled states, and table headers.
- **Structural Dividers (`#E2E8F0`):** Crisp 1px geometric delineations across all panels and tabular data.
- **Border Focus / Hover (`#94A3B8`):** Subtle border contrast shifts during active spatial navigation.

### Typography Scales
- **Text Dominant (`#0F172A`):** Core patient identifiers, metric values, and primary headers.
- **Text Substantive (`#334155`):** Standard clinical body copy, labels, and table cells.
- **Text Diminished (`#64748B`):** Auxiliary units, coordinate axis annotations, timestamps, and DICOM tags.

### Clinical Status & Tolerance System
- **Pass / Tolerance Met (`#059669`):** Indicates verified gamma passing criteria (e.g., >95% at 3%/2mm), target dose coverage conformality, and approved plan statuses.
- **Warning / Review Required (`#D97706`):** Indicates interpolation warnings, CT-MRI registration discrepancies, grid resampling artifacts, or borderline organ-at-risk (OAR) limits.
- **Critical / Interruption (`#DC2626`):** Signifies missing RTDOSE, failed QA tolerance, invalid contours, coordinate collisions, or unapproved plan delivery.

## Typography

Typography handles complex medical notations, tabular dose columns, and full Vietnamese diacritics with high vertical stability.

- **Primary Typeface (`Inter`):** Selected for clinical legibility, open apertures, and native support for tabular figures (`font-variant-numeric: tabular-nums`). Tabular numbers must be activated by default across all clinical tables and metric panels to prevent layout shift during realtime parameter streaming.
- **Monospaced Typeface (`JetBrains Mono`):** Dedicated to DICOM SOP Instance UIDs, SHA-256 integrity checksums, MLC leaf coordinate values, isocenter positions `(X, Y, Z)`, and raw hardware telemetry.
- **Capitalization & Hierarchy:** Uppercase typography is restricted strictly to micro-labels (`label-caps`) such as metadata headers (`DOSE GRID`, `ISOCENTER`, `ALGORITHM`) to anchor visual scanning without crowding the UI.

## Layout & Spacing

The interface uses a calibrated **12-column adaptive fluid framework** with a primary focus on high-efficiency, multi-panel workstation ergonomics:

### Clinical 3-Column Panel Architecture
- **Left Panel (Structure & Plan Index, 260px – 320px):** Collapsible sidebar listing DICOM series, RTSTRUCT contours, organ-at-risk lists, and isodose level toggles.
- **Center Canvas (Viewport & Cross-Section, Flexible Min-Width 640px):** Houses axial, sagittal, coronal CT views and 2D/3D Dose distributions. Maintains strict 1:1 aspect ratios where physical accuracy is mandatory.
- **Right Panel (Metrics & Inspector, 340px – 420px):** Hosts Dose Volume Histogram (DVH) statistics, gamma index summaries, dose constraint matrices, and approval sign-off blocks.

### Densities & Rhythms
- **Base Grid:** Built on a 4px sub-grid with an 8px structural layout cadence.
- **Dense Mode:** Table cells use 6px vertical padding (`space-xs` + `space-2xs`) and 8px horizontal padding (`space-sm`) to maximize visible contour records per screen without scrolling.
- **Panel Gaps:** Standardized to `12px` (`grid-gutter`) to conserve display surface while preserving immediate visual partition.

## Elevation & Depth

This system avoids heavy, atmospheric drop shadows that introduce visual noise or interfere with grey-level diagnostic imaging review. Visual hierarchy relies on **crisp, low-contrast structural outlines** and **surface tonal stepping**:

- **Layer 0 (Canvas Base):** `#F8FAFC` - Default background canvas.
- **Layer 1 (Card & Modular Panel):** `#FFFFFF` bordered with `1px solid #E2E8F0`. No drop shadow in resting state.
- **Layer 2 (Overlays, Dropdowns, Flyouts):** `#FFFFFF` with `1px solid #CBD5E1` and a surgical utility shadow: `box-shadow: 0 4px 12px -2px rgba(15, 39, 68, 0.08), 0 2px 4px -1px rgba(15, 39, 68, 0.04)`.
- **Layer 3 (Modals, Critical Alerts):** `#FFFFFF` with `1px solid #94A3B8` and a focused elevation shadow: `box-shadow: 0 12px 24px -4px rgba(15, 39, 68, 0.14)`. Backdrop is dimmed with `#0F172A` at 40% opacity.
- **Active State / Selection:** Indicated via a 2px interior border using Teal `#0D9488` or Primary Navy `#0F2744`, never through blur expansion.

## Shapes

The design uses a restrained, structural shape profile (`roundedness: 1`):

- **Core Radius (`4px` / `0.25rem`):** Applied uniformly to inputs, metric badges, buttons, segmented controls, and panel containers. Reflects precise medical engineering.
- **Tight Radius (`2px` / `0.125rem`):** Applied to inline tags, table-row highlight indicators, checkbox controls, and MLC progress bars.
- **Expanded Radius (`6px` / `0.375rem`):** Used solely for clinical dialog modals and floating viewport HUD controls.
- **Zero Radius (`0px`):** Applied to viewport render viewports, crosshair overlays, DVH chart drawing areas, and continuous multi-segment control buttons to retain absolute geometric alignment.

## Components

### Buttons
- **Primary:** Solid `#0F2744`, text `#FFFFFF`, height `32px` (dense) or `36px` (regular), `font-weight: 500`. Hover: `#1E3A8A`. Active: `#0A1B30`. Focus: `2px` ring `#0D9488` offset by `1px`.
- **Secondary / Ghost:** Transparent background, `1px solid #E2E8F0`, text `#334155`. Hover: `#F1F5F9`, border `#CBD5E1`.
- **Destructive / Reject:** Border `#FCA5A5`, background `#FEF2F2`, text `#DC2626`. Hover: background `#FEE2E2`.

### Metric Cards (Dose & Tolerance Indicators)
- Structured with a `3-part vertical layout`:
  1. Top: Uppercase label (`11px`, `#64748B`) + Status Pill (Pass/Warn/Fail).
  2. Middle: Large metric value (`24px` or `28px`, `#0F172A`, tabular) + explicit unit (`Gy`, `cGy`, `%`, `mm`) in `#64748B` (`13px`).
  3. Bottom: Tolerance rule (e.g., `Max ≤ 45.00 Gy | Margin: +1.24 Gy`) in `11px` JetBrains Mono.
- Left-edge status indicator: `3px` solid accent band (`#059669` for pass, `#D97706` for warning, `#DC2626` for critical).

### Data Tables (DICOM Structures & QA Results)
- Header height: `28px`, background `#F8FAFC`, text `#64748B`, uppercase `11px`, border-bottom `1px solid #CBD5E1`.
- Row height: `32px` compact. Hover state: `#F1F5F9`. Selected row: `#F0FDFA` with a `2px` left border in `#0D9488`.
- Values use mono or tabular figures, right-aligned for numeric data, left-aligned for structure names.

### Form Inputs & Adjusters
- Height: `32px`, border `1px solid #CBD5E1`, background `#FFFFFF`, text `#0F172A`, font-size `13px`.
- Direct numeric inputs (e.g., dose targets, coordinate offsets) incorporate clear right-pinned unit badges (`Gy`, `mm`) styled in `#64748B`.

### Status Badges & Chips
- Padding: `2px 6px`, border-radius `2px`, typography `11px`, `font-weight: 600`.
- **Pass Badge:** `#ECFDF5` background, `#059669` text, `#A7F3D0` border.
- **Warning Badge:** `#FFFBEB` background, `#D97706` text, `#FDE68A` border.
- **Error Badge:** `#FEF2F2` background, `#DC2626` text, `#FECACA` border.
- **Info / Metadata Badge:** `#F0F9FF` background, `#0284C7` text, `#BAE6FD` border.

### Checkboxes & Segmented Controls
- Checkbox size: `14px x 14px`, `2px` corner radius. Checked: background `#0F2744`, white surgical checkmark.
- Segmented Viewport Switcher (Axial, Sagittal, Coronal, 3D): Contained within a `#F1F5F9` border frame, active tab switches to `#FFFFFF` with a crisp `1px solid #CBD5E1` and bold primary typography.