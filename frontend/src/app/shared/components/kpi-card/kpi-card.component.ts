import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-kpi-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex flex-col justify-between gap-space-sm relative overflow-hidden group hover:shadow-md transition-shadow">
      <div class="flex items-center justify-between">
        <span class="font-label-sm text-label-sm text-outline uppercase tracking-wide">{{ label }}</span>
        <span 
          class="material-symbols-outlined text-[20px]"
          [ngClass]="getIconColor()">
          {{ icon }}
        </span>
      </div>
      
      <div class="flex items-baseline gap-space-sm">
        <span class="font-metric-lg text-metric-lg" [ngClass]="getValueColor()">{{ value }}</span>
        <span class="font-body-sm text-body-sm text-outline">{{ subtitle }}</span>
      </div>
      
      <div [ngClass]="getBadgeClasses()">
        <span [ngClass]="getBadgeDotClasses()"></span>
        {{ badge }}
      </div>
    </div>
  `,
  styles: []
})
export class KpiCardComponent {
  @Input() label: string = '';
  @Input() icon: string = '';
  @Input() value: string = '';
  @Input() subtitle: string = '';
  @Input() badge: string = '';
  @Input() status: 'default' | 'critical' | 'warning' | 'favorable' | 'pending' = 'default';

  getIconColor(): string {
    const colors: Record<string, string> = {
      default: 'text-outline',
      critical: 'text-error',
      warning: 'text-amber-700',
      favorable: 'text-secondary',
      pending: 'text-outline'
    };
    return colors[this.status] || colors['default'];
  }

  getValueColor(): string {
    const colors: Record<string, string> = {
      default: 'text-primary',
      critical: 'text-on-error-container',
      warning: 'text-primary',
      favorable: 'text-primary',
      pending: 'text-outline'
    };
    return colors[this.status] || colors['default'];
  }

  getBadgeClasses(): string {
    const baseClasses = 'inline-flex items-center gap-1.5 px-space-sm py-0.5 rounded-full text-[11px] font-semibold w-fit';
    const statusClasses: Record<string, string> = {
      default: 'bg-surface-container text-on-surface-variant',
      critical: 'bg-error-container/60 text-on-error-container',
      warning: 'bg-amber-100 text-amber-900',
      favorable: 'bg-secondary-container text-on-secondary-container',
      pending: 'bg-surface-container text-on-surface-variant'
    };
    return `${baseClasses} ${statusClasses[this.status] || statusClasses['default']}`;
  }

  getBadgeDotClasses(): string {
    const dotColors: Record<string, string> = {
      default: 'bg-outline',
      critical: 'bg-error',
      warning: 'bg-amber-600',
      favorable: 'bg-secondary',
      pending: 'bg-outline'
    };
    return `w-1.5 h-1.5 rounded-full ${dotColors[this.status] || dotColors['default']}`;
  }
}
