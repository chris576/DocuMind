import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { DocumentsController } from './documents.controller';
import { DocumentsService } from './documents.service';
import { PaperlessConnector } from './connectors/paperless.connector';
import { DocumentConnectorRegistry } from './connectors/document-connector.registry';
import { DOCUMENT_CONNECTOR } from './connectors/document-connector.interface';

@Module({
  imports: [HttpModule],
  controllers: [DocumentsController],
  providers: [
    PaperlessConnector,
    DocumentConnectorRegistry,
    {
      provide: DOCUMENT_CONNECTOR,
      inject: [DocumentConnectorRegistry, ConfigService],
      useFactory: (registry: DocumentConnectorRegistry, config: ConfigService) =>
        registry.get(config.get<string>('DOCUMENT_CONNECTOR_TYPE', 'paperless')),
    },
    DocumentsService,
  ],
  exports: [DocumentsService],
})
export class DocumentsModule {}
