---
name: Executive Precision Dark
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#b9c8de'
  on-secondary: '#233143'
  secondary-container: '#39485a'
  on-secondary-container: '#a7b6cc'
  tertiary: '#ffb786'
  on-tertiary: '#502400'
  tertiary-container: '#df7412'
  on-tertiary-container: '#461f00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#d4e4fa'
  secondary-fixed-dim: '#b9c8de'
  on-secondary-fixed: '#0d1c2d'
  on-secondary-fixed-variant: '#39485a'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb786'
  on-tertiary-fixed: '#311400'
  on-tertiary-fixed-variant: '#723600'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 8px
  margin-mobile: 16px
  margin-desktop: 32px
  gutter: 24px
  container-max: 1280px
---

## Brand & Style
The design system embodies a high-performance, elite atmosphere tailored for executive decision-making and technical precision. It leverages a **Corporate Modern** aesthetic infused with **Minimalist** principles to ensure that data remains the protagonist. 

The personality is authoritative, sophisticated, and focused. By utilizing a premium dark interface, the design system minimizes eye strain during long periods of deep work and creates a sense of "command center" reliability. The visual language favors sharp execution, clear hierarchy, and an absence of unnecessary ornamentation, evoking an emotional response of confidence and absolute control.

## Colors
The palette is anchored by a near-black **#0A0A0A** base, providing a "true dark" canvas that recedes into the background. Depth is communicated through a series of monochromatic neutral grays rather than shadows, creating a sophisticated layered effect.

The **Primary Blue** is tuned for high vibrancy on dark backgrounds, acting as a beacon for interaction. Semantic colors (Critical, Warning, Concern) have been shifted toward higher-value, slightly desaturated tones to ensure they meet WCAG AA contrast ratios against the dark surfaces without causing visual vibration. Use the "Sunken" value for input fields and "Elevated" values for modular components.

## Typography
This design system utilizes **Inter** exclusively to maintain a systematic, utilitarian, and highly legible interface. On dark backgrounds, text weights are meticulously balanced: headlines use a bold weight to command attention, while body text is kept at a regular weight with slightly increased line-height to prevent "ink-clogging" visual fatigue.

Letter spacing is tightened for large headings to maintain a compact, "engineered" look and slightly widened for small labels to improve scannability. Hierarchy is achieved through both size and color—primary information is set in high-contrast white, while secondary information is set in muted grays.

## Layout & Spacing
The layout follows a rigorous **8px grid system**, ensuring every element is mathematically aligned. It uses a **Fixed Grid** approach for desktop views to maintain focus and prevent information density from becoming overwhelming on ultra-wide monitors.

- **Desktop:** 12-column grid with 24px gutters and 32px outer margins.
- **Tablet:** 8-column grid with 20px gutters and 24px margins.
- **Mobile:** 4-column grid with 16px gutters and 16px margins.

Spacing should be used to group related information tightly (8px or 16px) while using larger gaps (32px or 48px) to clearly separate distinct functional sections.

## Elevation & Depth
In this premium dark environment, depth is not conveyed through heavy shadows, but through **Tonal Layering** and **Low-Contrast Outlines**.

Higher elevation is indicated by lighter surface colors. A card "hovering" over the base surface will use the `elevated-low` gray (#171717) and a subtle 1px border (#262626). Shadows, if used, should be extremely diffuse (20-30px blur), low-opacity (40%), and purely black to avoid washing out the background. This "stealth" approach to depth reinforces the professional, technical nature of the design system.

## Shapes
The shape language is defined by **Soft** geometry (4px radius). This slight rounding removes the "aggression" of sharp 90-degree corners while maintaining a more professional and disciplined look than pill-shaped or highly rounded elements. 

Consistency is key: buttons, input fields, and containers all share this 4px base radius. For larger containers or cards, a `rounded-lg` (8px) may be used to provide a subtle visual nesting effect.

## Components

### Buttons
- **Primary:** Solid Primary Blue with white text. No gradient. 4px radius.
- **Secondary:** Transparent background with a 1px `elevated-mid` border. Text in secondary color.
- **Ghost:** No border or background. Used for low-priority actions like "Cancel."

### Input Fields
- Use the `sunken` (#000000) background to create a "well" effect. 
- Border should be `elevated-low` (#171717), turning Primary Blue on focus.
- Placeholder text must be at least 4.5:1 contrast against the sunken background.

### Cards & Containers
- Containers should use `elevated-low` backgrounds.
- Headers within cards should be separated by a 1px line using the `elevated-mid` color.

### Chips & Badges
- Used for status indicators. Use semantic colors with a 10% opacity background and a solid 100% opacity text color for maximum readability and a premium "glass" look.

### Lists
- Interactive list items should use a subtle background color change (`elevated-mid`) on hover to provide clear feedback in the dark UI.