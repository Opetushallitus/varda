from xlsxwriter import Workbook
from xlsxwriter.worksheet import Worksheet, convert_cell_args


class AutofitWorksheet(Worksheet):
    """
    Extends xlsxwriter.worksheet.Worksheet to support column autofit width
    https://xlsxwriter.readthedocs.io/example_inheritance2.html

    Also keeps track of number of rows
    """

    def __init__(self):
        super().__init__()
        self.min_width = 0
        self.last_row = 0
        self.max_column_widths = {}

    @convert_cell_args
    def write(self, row, col, *args):
        result = super(AutofitWorksheet, self).write(row, col, *args)

        if not result < 0:
            # No errors
            value_len = len(str(args[0]))
            # Set width relative to number of characters to better keep the width consistent across columns
            # In Excel the column width depends on the font etc.
            value_width = value_len * (0.9**value_len + 1)
            max_width = self.max_column_widths.get(col, self.min_width)
            if value_width > max_width:
                self.max_column_widths[col] = value_width

        if row > self.last_row:
            self.last_row = row

        return result


class AutofitWorkbook(Workbook):
    """
    Extends xlsxwriter.Workbook to support column autofit width
    https://xlsxwriter.readthedocs.io/example_inheritance2.html

    Also keeps track of number of rows per worksheet
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.number_of_rows_per_worksheet = []

    def add_worksheet(self, *args, **kwargs):
        worksheet = super(AutofitWorkbook, self).add_worksheet(*args, **kwargs, worksheet_class=AutofitWorksheet)
        return worksheet

    def close(self):
        for worksheet in self.worksheets():
            for column, width in worksheet.max_column_widths.items():
                worksheet.set_column(column, column, width)
            self.number_of_rows_per_worksheet.append(worksheet.last_row)
        return super(AutofitWorkbook, self).close()
