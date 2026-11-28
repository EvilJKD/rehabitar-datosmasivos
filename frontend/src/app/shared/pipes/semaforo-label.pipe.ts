import { Pipe, PipeTransform } from '@angular/core';
import { Semaforo } from '../../core/models/municipio.model';

const ETIQUETAS: Record<Semaforo, string> = {
  VERDE: 'Seguro',
  AMBAR: 'Precaución',
  ROJO: 'Peligro',
  PENDIENTE: 'Pendiente',
};

@Pipe({ name: 'semaforoLabel', standalone: true })
export class SemaforoLabelPipe implements PipeTransform {
  transform(semaforo: Semaforo | null | undefined): string {
    return ETIQUETAS[semaforo ?? 'PENDIENTE'];
  }
}
