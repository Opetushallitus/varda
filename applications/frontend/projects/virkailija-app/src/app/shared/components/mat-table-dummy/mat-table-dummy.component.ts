import { Component } from '@angular/core';

@Component({
    selector: 'app-mat-table-dummy',
    template: `
    <mat-table class="d-none">
      <tr mat-row *matRowDef="let row; columns: [];"></tr>
    </mat-table>
  `,
    standalone: false
})
export class MatTableDummyComponent {
  /**
   * Dummy component for initializing a minimal instance of MatTable so that its styles are imported.
   */
  constructor() { }
}
