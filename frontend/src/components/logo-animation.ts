/**
 * Interactive logo animation that makes the tail follow the cursor
 * and animates stat bar heights based on cursor angle
 */

interface LogoElements {
    wrapper: HTMLElement;
    tailLight: SVGPolygonElement;
    tailDark: SVGPolygonElement;
    bar1Light: SVGRectElement;
    bar2Light: SVGRectElement;
    bar3Light: SVGPathElement;
    bar1Dark: SVGRectElement;
    bar2Dark: SVGRectElement;
    bar3Dark: SVGPathElement;
}

// Configuration
const ACTIVATION_RADIUS = 150; // Distance in pixels to activate the animation (reduced from 200)
const LOGO_CENTER = { x: 100, y: 100 }; // Center point in SVG viewBox coordinates
const BASE_HEIGHTS = { bar1: 30, bar2: 50, bar3: 40 }; // Base heights for the stat bars
const HEIGHT_VARIATION = 25; // How much the heights can vary

export class LogoAnimation {
    private elements: LogoElements | null = null;
    private isActive = false;
    private logoRect: DOMRect | null = null;
    private animationFrameId: number | null = null;

    constructor() {
        this.handleMouseMove = this.handleMouseMove.bind(this);
        this.updateAnimation = this.updateAnimation.bind(this);
    }

    /**
     * Initialize the logo animation
     */
    public init(): void {
        const wrapper = document.getElementById('logoWrapper');
        if (!wrapper) {
            console.warn('Logo wrapper not found');
            return;
        }

        // Get all the elements we need to manipulate
        this.elements = {
            wrapper,
            tailLight: document.getElementById('logoTailLight') as SVGPolygonElement,
            tailDark: document.getElementById('logoTailDark') as SVGPolygonElement,
            bar1Light: document.getElementById('logoBar1Light') as SVGRectElement,
            bar2Light: document.getElementById('logoBar2Light') as SVGRectElement,
            bar3Light: document.getElementById('logoBar3Light') as SVGPathElement,
            bar1Dark: document.getElementById('logoBar1Dark') as SVGRectElement,
            bar2Dark: document.getElementById('logoBar2Dark') as SVGRectElement,
            bar3Dark: document.getElementById('logoBar3Dark') as SVGPathElement,
        };

        // Verify all elements exist
        if (!this.verifyElements()) {
            console.warn('Some logo elements not found');
            return;
        }

        // Add event listener for mouse movement
        document.addEventListener('mousemove', this.handleMouseMove);

        // Update logo rect on window resize
        window.addEventListener('resize', () => {
            this.logoRect = null;
        });
    }

    /**
     * Verify all required elements exist
     */
    private verifyElements(): boolean {
        if (!this.elements) return false;

        return !!(
            this.elements.wrapper &&
            this.elements.tailLight &&
            this.elements.tailDark &&
            this.elements.bar1Light &&
            this.elements.bar2Light &&
            this.elements.bar3Light &&
            this.elements.bar1Dark &&
            this.elements.bar2Dark &&
            this.elements.bar3Dark
        );
    }

    /**
     * Get the logo's bounding rectangle (always fresh)
     */
    private getLogoRect(): DOMRect {
        // Always get fresh rect to handle position changes
        if (this.elements) {
            return this.elements.wrapper.getBoundingClientRect();
        }
        return this.logoRect!;
    }

    /**
     * Handle mouse move event
     */
    private handleMouseMove(event: MouseEvent): void {
        if (!this.elements) return;

        // Get fresh position each time
        const rect = this.getLogoRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        // Calculate distance from cursor to logo center
        const dx = event.clientX - centerX;
        const dy = event.clientY - centerY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Check if cursor is within activation radius
        if (distance <= ACTIVATION_RADIUS) {
            if (!this.isActive) {
                this.isActive = true;
                this.elements.wrapper.classList.add('logo-active');
            }
            this.updateAnimation(dx, dy, distance);
        } else {
            if (this.isActive) {
                this.isActive = false;
                this.elements.wrapper.classList.remove('logo-active');
                this.resetLogo();
            }
        }
    }

    /**
     * Update the logo animation based on cursor position
     */
    private updateAnimation(dx: number, dy: number, distance: number): void {
        if (!this.elements) return;

        // Calculate angle in radians (-π to π)
        const angle = Math.atan2(dy, dx);

        // Convert to degrees (0-360)
        const degrees = ((angle * 180 / Math.PI) + 360) % 360;

        // Update tail direction
        this.updateTail(angle, distance);

        // Update bar heights based on angle
        this.updateBarHeights(degrees);
    }

    /**
     * Update the tail to point toward the cursor
     */
    private updateTail(angle: number, distance: number): void {
        if (!this.elements) return;

        // Calculate tail anchor point on the circle (same side as cursor, pointing toward it)
        const tailBaseAngle = angle;
        const circleRadius = 75;

        // Calculate the tail width (angular spread) - narrower tail
        const tailWidthAngle = 0.25; // radians

        // Three anchor points on the circle edge
        const anchor1Angle = tailBaseAngle - tailWidthAngle;
        const anchor2Angle = tailBaseAngle + tailWidthAngle;
        const anchorCenterAngle = tailBaseAngle;

        const anchor1X = LOGO_CENTER.x + Math.cos(anchor1Angle) * circleRadius;
        const anchor1Y = LOGO_CENTER.y + Math.sin(anchor1Angle) * circleRadius;

        const anchor2X = LOGO_CENTER.x + Math.cos(anchor2Angle) * circleRadius;
        const anchor2Y = LOGO_CENTER.y + Math.sin(anchor2Angle) * circleRadius;

        // Center anchor for smoother connection
        const anchorCenterX = LOGO_CENTER.x + Math.cos(anchorCenterAngle) * circleRadius;
        const anchorCenterY = LOGO_CENTER.y + Math.sin(anchorCenterAngle) * circleRadius;

        // Tail tip (extends outward from the circle) - shorter length
        const tailLength = Math.min(30, 25 + distance / 30); // Reduced length
        const tipX = LOGO_CENTER.x + Math.cos(tailBaseAngle) * (circleRadius + tailLength);
        const tipY = LOGO_CENTER.y + Math.sin(tailBaseAngle) * (circleRadius + tailLength);

        // Create polygon points: anchor1 -> tip -> anchor2 -> anchorCenter (back to circle)
        const points = `${anchor1X},${anchor1Y} ${tipX},${tipY} ${anchor2X},${anchor2Y} ${anchorCenterX},${anchorCenterY}`;

        // Update both light and dark versions
        this.elements.tailLight.setAttribute('points', points);
        this.elements.tailDark.setAttribute('points', points);
    }

    /**
     * Update bar heights based on angle
     */
    private updateBarHeights(degrees: number): void {
        if (!this.elements) return;

        // Use sine waves at different phases to create varying heights
        const radians = degrees * Math.PI / 180;

        // Each bar has a different phase offset
        const height1 = BASE_HEIGHTS.bar1 + Math.sin(radians) * HEIGHT_VARIATION;
        const height2 = BASE_HEIGHTS.bar2 + Math.sin(radians + Math.PI * 2/3) * HEIGHT_VARIATION;
        const height3 = BASE_HEIGHTS.bar3 + Math.sin(radians + Math.PI * 4/3) * HEIGHT_VARIATION;

        // Update bar1 (simple rect)
        const bar1Y = 125 - height1;
        this.elements.bar1Light.setAttribute('y', bar1Y.toString());
        this.elements.bar1Light.setAttribute('height', height1.toString());
        this.elements.bar1Dark.setAttribute('y', bar1Y.toString());
        this.elements.bar1Dark.setAttribute('height', height1.toString());

        // Update bar2 (simple rect)
        const bar2Y = 125 - height2;
        this.elements.bar2Light.setAttribute('y', bar2Y.toString());
        this.elements.bar2Light.setAttribute('height', height2.toString());
        this.elements.bar2Dark.setAttribute('y', bar2Y.toString());
        this.elements.bar2Dark.setAttribute('height', height2.toString());

        // Update bar3 (path with rounded corners) - more complex
        this.updateBar3Path(height3, this.elements.bar3Light, 124.942);
        this.updateBar3Path(height3, this.elements.bar3Dark, 124.76);
    }

    /**
     * Update the path for bar3 which has rounded corners
     */
    private updateBar3Path(height: number, element: SVGPathElement, xStart: number): void {
        const y1 = 125 - height;
        const y2 = 125;
        const rx = 7;

        // Recreate the rounded rectangle path
        const xEnd = 150;
        const width = xEnd - xStart - 2 * rx;

        const path = `M${xStart} ${y1 + rx}C${xStart} ${y1 + rx * 0.448} ${xStart + rx * 0.448} ${y1} ${xStart + rx} ${y1}H${xStart + rx + width}C${xStart + 2*rx + width - rx*0.448} ${y1} ${xStart + 2*rx + width} ${y1 + rx*0.448} ${xStart + 2*rx + width} ${y1 + rx}V${y2 - rx}C${xStart + 2*rx + width} ${y2 - rx*0.448} ${xStart + 2*rx + width - rx*0.448} ${y2} ${xStart + rx + width} ${y2}H${xStart + rx}C${xStart + rx*0.448} ${y2} ${xStart} ${y2 - rx*0.448} ${xStart} ${y2 - rx}V${y1 + rx}Z`;

        element.setAttribute('d', path);
    }

    /**
     * Reset logo to its default state
     */
    private resetLogo(): void {
        if (!this.elements) return;

        // Reset tail to original position (bottom-left, pointing to lower-left)
        const originalTailPoints = "62.71,165.09 34.89,137.26 29.72,173.93";

        this.elements.tailLight.setAttribute('points', originalTailPoints);
        this.elements.tailDark.setAttribute('points', originalTailPoints);

        // Reset bars to original heights
        this.elements.bar1Light.setAttribute('y', '95');
        this.elements.bar1Light.setAttribute('height', '30');
        this.elements.bar1Dark.setAttribute('y', '95');
        this.elements.bar1Dark.setAttribute('height', '30');

        this.elements.bar2Light.setAttribute('y', '75');
        this.elements.bar2Light.setAttribute('height', '50');
        this.elements.bar2Dark.setAttribute('y', '75');
        this.elements.bar2Dark.setAttribute('height', '50');

        // Reset bar3 paths
        const originalBar3PathLight = "M124.942 92C124.942 88.134 128.076 85 131.942 85H143C146.866 85 150 88.134 150 92V118C150 121.866 146.866 125 143 125H131.942C128.076 125 124.942 121.866 124.942 118V92Z";
        const originalBar3PathDark = "M124.76 92C124.76 88.134 127.894 85 131.76 85H143C146.866 85 150 88.134 150 92V118C150 121.866 146.866 125 143 125H131.76C127.894 125 124.76 121.866 124.76 118V92Z";

        this.elements.bar3Light.setAttribute('d', originalBar3PathLight);
        this.elements.bar3Dark.setAttribute('d', originalBar3PathDark);
    }

    /**
     * Cleanup event listeners
     */
    public destroy(): void {
        document.removeEventListener('mousemove', this.handleMouseMove);
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
        }
    }
}

// Export a function to initialize the logo animation
export function initLogoAnimation(): void {
    const animation = new LogoAnimation();
    animation.init();
}
