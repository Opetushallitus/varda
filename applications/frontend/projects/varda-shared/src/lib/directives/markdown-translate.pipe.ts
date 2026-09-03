import { Pipe, PipeTransform } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';
import { marked } from 'marked';

// Add target="_blank" to marked generated links
// https://github.com/markedjs/marked/issues/655#issuecomment-712380889
const renderer = new marked.Renderer();
const linkRenderer = renderer.link;
renderer.link = (href, title, text) => {
  const localLink = href.startsWith(`${location.protocol}//${location.hostname}`);
  const html = linkRenderer.call(renderer, href, title, text);
  return localLink ? html : html.replace(/^<a /, '<a target="_blank" rel="noopener" ');
};
marked.use({
  tokenizer: {
    // Disable marked autolinks for URLs and emails
    url: () => {}
  },
  renderer
});

/**
 * Extend TranslatePipe to support Markdown styling
 */
@Pipe({
    name: 'translateMarkdown',
    pure: false,
    standalone: false
})
export class MarkdownTranslatePipe extends TranslatePipe implements PipeTransform {
  transform(query: string, ...args): any {
    let parseMarkdown = true;
    // Do not parse markdown if markdown argument is false
    if (args.length > 0 && args[0]?.markdown === false) {
      parseMarkdown = false;
      // Copy options object and remove markdown property, so that it is not passed to TranslatePipe and is not removed
      // from the original arguments
      args[0] = {...args[0]};
      delete args[0].markdown;
    }

    // Get the initial translation
    let value = super.transform(query, ...args);

    if (parseMarkdown && value && typeof value === 'string') {
      // Parse Markdown notations, trim whitespace, restore escaped quotes
      value = marked(value).trim().replaceAll('&quot;', '"').replaceAll('&#39;', '\'');

      // If value is wrapped in <p> tags, remove them (only single pair of <p> tags present)
      if (value.startsWith('<p>') && value.endsWith('</p>') && (value.match(/<p>/g) || []).length === 1) {
        value = value.substring(3, value.length - 4);
      }
    }

    return value;
  }
}
