import { Routes } from '@angular/router';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { MunicipioDetailComponent } from './pages/municipio-detail/municipio-detail.component';
import { ConvocatoriasComponent } from './pages/convocatorias/convocatorias.component';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'municipio/:codigo_ine', component: MunicipioDetailComponent },
  { path: 'convocatorias', component: ConvocatoriasComponent },
  { path: '**', redirectTo: '/dashboard' },
];
