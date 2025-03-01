extension CaseConversionStringExt on String {
  String toCapitalizedCase() {
    return toLowerCase().replaceAllMapped(RegExp(r'(^|\s|-)[a-ząćęłńóśźż]'), (match) => match.group(0)!.toUpperCase());
  }
}
