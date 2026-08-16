import { Injectable } from '@nestjs/common';
import { DocumentConnector } from './document-connector.interface';
import { PaperlessConnector } from './paperless.connector';

/**
 * Holds all registered document connectors and resolves them by their `type`.
 *
 * Adding a new connector = implement {@link DocumentConnector}, inject it into
 * the constructor below, and call {@link register}. No changes to the
 * selection logic are required.
 */
@Injectable()
export class DocumentConnectorRegistry {
  private readonly connectors = new Map<string, DocumentConnector>();

  constructor(paperless: PaperlessConnector) {
    this.register(paperless);
  }

  register(connector: DocumentConnector): void {
    this.connectors.set(connector.type, connector);
  }

  get(type: string): DocumentConnector {
    const connector = this.connectors.get(type);
    if (!connector) {
      throw new Error(
        `Unsupported document connector type "${type}". ` +
          `Available types: ${this.listTypes().join(', ') || '(none)'}`,
      );
    }
    return connector;
  }

  listTypes(): string[] {
    return Array.from(this.connectors.keys());
  }
}
